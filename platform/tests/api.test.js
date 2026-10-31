// Unit tests that need no database: run with `npm test` in platform/api.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createApp, parseCookies } from "../api/src/server.js";

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
