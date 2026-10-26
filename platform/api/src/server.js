// SCC26 Student Project Platform API (Week 3, platform/README.md).
// Serves the static Astro build and a small authenticated JSON API.
import crypto from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import bcrypt from "bcryptjs";
import express from "express";
import client from "prom-client";
import { migrate, pool, seed } from "./db.js";

const PORT = Number(process.env.PORT || 8080);
const SESSION_HOURS = Number(process.env.SESSION_HOURS || 12);
const COOKIE = "scc26_session";
const STATIC_DIR =
  process.env.STATIC_DIR || path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public");
const startedAt = new Date();

// Prometheus metrics with bounded labels only (docs/EXPERIMENT-PROVENANCE.md).
const register = new client.Registry();
client.collectDefaultMetrics({ register });
const httpRequests = new client.Counter({
  name: "platform_http_requests_total",
  help: "HTTP requests",
  labelNames: ["route", "status"],
  registers: [register],
});
const logins = new client.Counter({
  name: "platform_logins_total",
  help: "Login attempts",
  labelNames: ["result"],
  registers: [register],
});

const sha256 = (s) => crypto.createHash("sha256").update(s).digest("hex");
export function parseCookies(header = "") {
  const out = {};
  for (const part of header.split(";")) {
    const i = part.indexOf("=");
    if (i > 0) out[part.slice(0, i).trim()] = part.slice(i + 1).trim();
  }
  return out;
}

export function createApp() {
  const app = express();
  app.disable("x-powered-by");
  app.use(express.json({ limit: "10kb" }));
  app.use((req, res, next) => {
    res.set({
      "Content-Security-Policy":
        "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
      "Strict-Transport-Security": "max-age=31536000",
      "X-Content-Type-Options": "nosniff",
      "X-Frame-Options": "DENY",
      "Referrer-Policy": "no-referrer",
    });
    res.on("finish", () =>
      httpRequests.inc({ route: req.route?.path || "static", status: String(res.statusCode) }),
    );
    next();
  });

  // Liveness: the process is up. Readiness: the database answers.
  app.get("/healthz", (_req, res) => res.json({ status: "ok" }));
  app.get("/health", async (_req, res) => {
    try {
      await pool.query("SELECT 1");
      res.json({ status: "ok", database: "ok" });
    } catch {
      res.status(503).json({ status: "degraded", database: "unreachable" });
    }
  });
  app.get("/metrics", async (_req, res) => {
    res.set("Content-Type", register.contentType);
    res.send(await register.metrics());
  });

  async function currentUser(req) {
    const token = parseCookies(req.headers.cookie)[COOKIE];
    if (!token) return null;
    const { rows } = await pool.query(
      `SELECT u.id, u.username, u.display_name, t.name AS team, t.project_slug
         FROM sessions s JOIN users u ON u.id = s.user_id LEFT JOIN teams t ON t.id = u.team_id
        WHERE s.token_hash = $1 AND s.expires_at > now()`,
      [sha256(token)],
    );
    return rows[0] || null;
  }
  async function requireUser(req, res, next) {
    const user = await currentUser(req);
    if (!user) return res.status(401).json({ error: "not signed in" });
    req.user = user;
    return next();
  }

  app.post("/api/login", async (req, res) => {
    const { username, password } = req.body || {};
    if (
      typeof username !== "string" ||
      typeof password !== "string" ||
      username.length > 64 ||
      password.length > 256
    ) {
      return res.status(400).json({ error: "username and password required" });
    }
    const { rows } = await pool.query("SELECT id, password_hash FROM users WHERE username = $1", [username]);
    const ok = Boolean(rows[0]) && (await bcrypt.compare(password, rows[0].password_hash));
    logins.inc({ result: ok ? "success" : "failure" });
    if (!ok) return res.status(401).json({ error: "invalid username or password" });
    const token = crypto.randomBytes(32).toString("base64url");
    await pool.query(
      "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES ($1, $2, now() + make_interval(hours => $3))",
      [sha256(token), rows[0].id, SESSION_HOURS],
    );
    await pool.query("INSERT INTO logins (user_id) VALUES ($1)", [rows[0].id]);
    res.cookie(COOKIE, token, {
      httpOnly: true,
      secure: true,
      sameSite: "strict",
      path: "/",
      maxAge: SESSION_HOURS * 3600e3,
    });
    return res.json({ ok: true });
  });

  app.post("/api/logout", async (req, res) => {
    const token = parseCookies(req.headers.cookie)[COOKIE];
    if (token) await pool.query("DELETE FROM sessions WHERE token_hash = $1", [sha256(token)]);
    res.clearCookie(COOKIE, { path: "/" });
    res.json({ ok: true });
  });

  app.get("/api/me", requireUser, (req, res) => res.json(req.user));

  // Safe status view: no credentials, no cluster access, only what the app knows.
  app.get("/api/status", requireUser, async (_req, res) => {
    const [{ rows: u }, { rows: l }, { rows: v }] = await Promise.all([
      pool.query("SELECT count(*)::int AS users FROM users"),
      pool.query("SELECT count(*)::int AS logins, max(at) AS last_login FROM logins"),
      pool.query("SHOW server_version"),
    ]);
    res.json({
      app_version: process.env.APP_VERSION || "dev",
      git_sha: process.env.GIT_SHA || "unknown",
      started_at: startedAt.toISOString(),
      uptime_seconds: Math.round(process.uptime()),
      database: {
        server_version: v[0].server_version,
        users: u[0].users,
        logins: l[0].logins,
        last_login: l[0].last_login,
      },
    });
  });

  app.use(express.static(STATIC_DIR, { extensions: ["html"] }));
  return app;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await migrate();
  await seed(bcrypt);
  createApp().listen(PORT, () => console.log(`student-platform listening on :${PORT}`));
}
