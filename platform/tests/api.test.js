// Unit tests that need no database: run with `npm test` in platform/api.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { pool } from "../api/src/db.js";
import {
  clearFailures,
  createApp,
  parseCookies,
  passwordProblem,
  recordFailure,
  tooManyFailures,
} from "../api/src/server.js";

let server;
let base;
before(async () => {
  server = createApp().listen(0);
  await new Promise((r) => server.once("listening", r));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => server.close());

test("parseCookies handles several cookies and '=' in values", () => {
  assert.deepEqual(parseCookies("a=1; scc26_session=abc=def; b=2"), { a: "1", scc26_session: "abc=def", b: "2" });
  assert.deepEqual(parseCookies(""), {});
});

test("liveness probe answers without a database", async () => {
  const r = await fetch(`${base}/healthz`);
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { status: "ok" });
});

test("security headers are set on every response", async () => {
  const r = await fetch(`${base}/healthz`);
  assert.match(r.headers.get("content-security-policy"), /default-src 'self'/);
  assert.equal(r.headers.get("x-frame-options"), "DENY");
  assert.equal(r.headers.get("x-content-type-options"), "nosniff");
  assert.equal(r.headers.get("x-powered-by"), null);
});

test("protected endpoints refuse requests without a session", async () => {
  for (const p of ["/api/me", "/api/status"]) {
    const r = await fetch(`${base}${p}`);
    assert.equal(r.status, 401, p);
  }
});

test("login rejects malformed input before touching the database", async () => {
  const r = await fetch(`${base}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: 1 }),
  });
  assert.equal(r.status, 400);
});

test("metrics endpoint exposes bounded platform counters", async () => {
  const text = await (await fetch(`${base}/metrics`)).text();
  assert.match(text, /platform_http_requests_total/);
  assert.match(text, /platform_logins_total/);
});

test("the PostgreSQL pool handles dropped connections instead of crashing", () => {
  // Regression: replacing postgres-0 crashed every platform pod (3 restarts each)
  // because the pool's 'error' event had no listener.
  assert.ok(pool.listenerCount("error") >= 1);
});

test("password policy: length, reuse and username", () => {
  assert.equal(passwordProblem("olerato", "old-password-1", "short"), "use at least 12 characters");
  assert.equal(passwordProblem("olerato", "same-password-1", "same-password-1"), "choose a password different from the current one");
  assert.equal(passwordProblem("olerato", "old-password-1", "Olerato-is-great-99"), "don't include your username");
  assert.equal(passwordProblem("olerato", "old-password-1", "purple teal mountain 42"), null);
});

test("login throttling kicks in after repeated failures and resets", () => {
  const key = "203.0.113.9|tester";
  clearFailures(key);
  for (let i = 0; i < 10; i += 1) recordFailure(key);
  assert.equal(tooManyFailures(key), true);
  clearFailures(key);
  assert.equal(tooManyFailures(key), false);
  // old failures fall out of the 15-minute window
  for (let i = 0; i < 10; i += 1) recordFailure(key, Date.now() - 16 * 60e3);
  assert.equal(tooManyFailures(key), false);
});

test("changing a password requires a session", async () => {
  const r = await fetch(`${base}/api/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password: "x", new_password: "y" }),
  });
  assert.equal(r.status, 401);
});

