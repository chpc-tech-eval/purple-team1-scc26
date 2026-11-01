// SCC26 Student Project Platform API (Week 3, platform/README.md).
// Serves the static Astro build and a small authenticated JSON API.
import crypto from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import bcrypt from "bcryptjs";
import express from "express";
import client from "prom-client";
import { migrate, pool, seed, waitForDatabase } from "./db.js";

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

// Brute-force guard: at most LOGIN_MAX_FAILURES failed sign-ins per client IP
// and username in LOGIN_WINDOW_MS (per pod; enough to stop online guessing).
const LOGIN_MAX_FAILURES = Number(process.env.LOGIN_MAX_FAILURES || 10);
const LOGIN_WINDOW_MS = Number(process.env.LOGIN_WINDOW_MS || 15 * 60e3);
const failures = new Map();
export function tooManyFailures(key, now = Date.now()) {
  const recent = (failures.get(key) || []).filter((t) => now - t < LOGIN_WINDOW_MS);
  failures.set(key, recent);
  return recent.length >= LOGIN_MAX_FAILURES;
}
export function recordFailure(key, now = Date.now()) {
  failures.set(key, [...(failures.get(key) || []), now]);
}
export function clearFailures(key) {
  failures.delete(key);
}

// Password policy for a password the user chooses.
export function passwordProblem(username, current, next) {
  if (typeof next !== "string" || next.length < 12) return "use at least 12 characters";
  if (next.length > 128) return "use at most 128 characters";
  if (next === current) return "choose a password different from the current one";
  if (next.toLowerCase().includes(String(username).toLowerCase())) return "don't include your username";
  return null;
}
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
  app.set("trust proxy", 1); // one hop: Traefik sets X-Forwarded-For
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
      `SELECT u.id, u.username, u.display_name, t.name AS team, t.project_slug,
              (u.password_changed_at IS NULL) AS must_change_password
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
  // Accounts still on a handed-out password may only change it.
  function requireOwnPassword(req, res, next) {
    if (req.user.must_change_password) {
      return res.status(403).json({ error: "set your own password first", must_change_password: true });
    }
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
    const key = `${req.ip}|${username.toLowerCase()}`;
    if (tooManyFailures(key)) {
      logins.inc({ result: "throttled" });
      return res.status(429).json({ error: "too many failed attempts; try again in 15 minutes" });
    }
    const { rows } = await pool.query(
      "SELECT id, password_hash, password_changed_at FROM users WHERE username = $1",
      [username],
    );
    const ok = Boolean(rows[0]) && (await bcrypt.compare(password, rows[0].password_hash));
    logins.inc({ result: ok ? "success" : "failure" });
    if (!ok) {
      recordFailure(key);
      return res.status(401).json({ error: "invalid username or password" });
    }
    clearFailures(key);
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
    return res.json({ ok: true, must_change_password: rows[0].password_changed_at === null });
  });

  // Change your own password: needs the current one; ends your other sessions.
  app.post("/api/password", requireUser, async (req, res) => {
    const { current_password: current, new_password: next } = req.body || {};
    if (typeof current !== "string" || current.length > 256) {
      return res.status(400).json({ error: "current password required" });
    }
    const { rows } = await pool.query("SELECT password_hash FROM users WHERE id = $1", [req.user.id]);
    if (!rows[0] || !(await bcrypt.compare(current, rows[0].password_hash))) {
      return res.status(401).json({ error: "current password is wrong" });
    }
    const problem = passwordProblem(req.user.username, current, next);
    if (problem) return res.status(400).json({ error: problem });
    const hash = await bcrypt.hash(next, 12);
    await pool.query("UPDATE users SET password_hash = $1, password_changed_at = now() WHERE id = $2", [
      hash,
      req.user.id,
    ]);
    const token = parseCookies(req.headers.cookie)[COOKIE];
    await pool.query("DELETE FROM sessions WHERE user_id = $1 AND token_hash <> $2", [req.user.id, sha256(token)]);
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
  app.get("/api/status", requireUser, requireOwnPassword, async (_req, res) => {
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
  await waitForDatabase();
  await migrate();
  await seed(bcrypt);
  createApp().listen(PORT, () => console.log(`student-platform listening on :${PORT}`));
}
