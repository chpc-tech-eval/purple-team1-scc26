// Crypty / ACP client tests (Week 4). No database and no real ACP needed.
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import {
  ACP_AUDIENCE,
  ACP_DIAGNOSTIC,
  ACP_ISSUER,
  ACP_SCOPE,
  acpConfig,
  acpRequest,
  browserResult,
  isUuid,
  signAssertion,
} from "../api/src/acp.js";
import { createApp } from "../api/src/server.js";

const { privateKey, publicKey } = crypto.generateKeyPairSync("ed25519");
const SUBJECT = "0b0c5f1e-2f7a-4c1d-9a3e-5d6f7a8b9c0d";

function decode(token) {
  const [h, p, s] = token.split(".");
  return {
    header: JSON.parse(Buffer.from(h, "base64url")),
    claims: JSON.parse(Buffer.from(p, "base64url")),
    valid: crypto.verify(null, Buffer.from(`${h}.${p}`), publicKey, Buffer.from(s, "base64url")),
  };
}

test("assertion is EdDSA, verifies with the public key and carries exactly ACP's claims", () => {
  const token = signAssertion({ subjectUuid: SUBJECT, tenant: "purple-team1", privateKey, now: 1000 });
  const { header, claims, valid } = decode(token);
  assert.equal(valid, true);
  assert.deepEqual(header, { alg: "EdDSA", typ: "JWT" });
  assert.equal(claims.iss, ACP_ISSUER);
  assert.equal(claims.aud, ACP_AUDIENCE);
  assert.equal(claims.sub, `urn:quantum-platform:user:${SUBJECT}`);
  assert.equal(claims.tenant, "purple-team1");
  assert.equal(claims.scope, ACP_SCOPE);
  assert.equal(claims.iat, 1000);
  assert.equal(claims.nbf, 1000);
  assert.ok(claims.exp - claims.iat <= 90, "ACP rejects lifetimes over 90 s");
  assert.ok(isUuid(claims.jti));
  assert.deepEqual(Object.keys(claims).sort(), ["aud", "exp", "iat", "iss", "jti", "nbf", "scope", "sub", "tenant"]);
});

test("a tampered assertion no longer verifies", () => {
  const token = signAssertion({ subjectUuid: SUBJECT, tenant: "purple-team1", privateKey });
  const [h, p, s] = token.split(".");
  const forged = Buffer.from(JSON.stringify({ ...decode(token).claims, scope: "agent:personal" })).toString("base64url");
  assert.equal(decode(`${h}.${forged}.${s}`).valid, false);
  assert.equal(p.length > 0, true);
});

test("signing refuses long lifetimes, non-UUID subjects and a missing tenant", () => {
  assert.throws(() => signAssertion({ subjectUuid: SUBJECT, tenant: "t", privateKey, lifetime: 91 }));
  assert.throws(() => signAssertion({ subjectUuid: SUBJECT, tenant: "t", privateKey, lifetime: 0 }));
  assert.throws(() => signAssertion({ subjectUuid: "phathutshedzo", tenant: "t", privateKey }));
  assert.throws(() => signAssertion({ subjectUuid: SUBJECT, tenant: "", privateKey }));
});

test("each call gets a fresh assertion (new jti)", () => {
  const a = decode(signAssertion({ subjectUuid: SUBJECT, tenant: "t", privateKey })).claims.jti;
  const b = decode(signAssertion({ subjectUuid: SUBJECT, tenant: "t", privateKey })).claims.jti;
  assert.notEqual(a, b);
});

let dir;
before(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "crypty-"));
});
after(() => fs.rmSync(dir, { recursive: true, force: true }));

test("config: unset means 'not configured'; bad URL or non-Ed25519 key fails loudly", () => {
  assert.equal(acpConfig({}), null);
  const ed = path.join(dir, "ed.pem");
  fs.writeFileSync(ed, privateKey.export({ type: "pkcs8", format: "pem" }));
  const ok = acpConfig({ ACP_URL: "http://acp:8080/", ACP_SIGNING_KEY_FILE: ed, ACP_TENANT_ID: "t", ACP_ALLOWED_USERS: "a, b,," });
  assert.equal(ok.url, "http://acp:8080");
  assert.deepEqual([...ok.allowed], ["a", "b"]);
  assert.throws(() => acpConfig({ ACP_URL: "http://u:p@acp:8080", ACP_SIGNING_KEY_FILE: ed, ACP_TENANT_ID: "t" }));
  assert.throws(() => acpConfig({ ACP_URL: "ftp://acp", ACP_SIGNING_KEY_FILE: ed, ACP_TENANT_ID: "t" }));
  const rsa = path.join(dir, "rsa.pem");
  fs.writeFileSync(
    rsa,
    crypto.generateKeyPairSync("rsa", { modulusLength: 2048 }).privateKey.export({ type: "pkcs8", format: "pem" }),
  );
  assert.throws(() => acpConfig({ ACP_URL: "http://acp:8080", ACP_SIGNING_KEY_FILE: rsa, ACP_TENANT_ID: "t" }));
});

test("request: bearer assertion, idempotency key, fixed diagnostic body, no redirects", async () => {
  const seen = {};
  const fakeFetch = async (url, init) => {
    Object.assign(seen, { url, init });
    return new Response(JSON.stringify({ task_id: SUBJECT, status: "queued" }), { status: 202 });
  };
  const cfg = { url: "http://acp:8080", tenant: "purple-team1", privateKey };
  const key = crypto.randomUUID();
  const r = await acpRequest(cfg, { agent_principal: SUBJECT }, "POST", "/v1/admin/tasks", {
    body: { diagnostic: ACP_DIAGNOSTIC },
    idempotencyKey: key,
    fetchImpl: fakeFetch,
  });
  assert.equal(r.status, 202);
  assert.equal(seen.url, "http://acp:8080/v1/admin/tasks");
  assert.equal(seen.init.redirect, "error");
  assert.equal(seen.init.headers["idempotency-key"], key);
  assert.deepEqual(JSON.parse(seen.init.body), { diagnostic: "quantum-platform-pod-readiness" });
  const { valid, claims } = decode(seen.init.headers.authorization.replace(/^Bearer /, ""));
  assert.equal(valid, true);
  assert.equal(claims.sub, `urn:quantum-platform:user:${SUBJECT}`);
});

test("ACP failures stay failures for the browser (never reported as success)", () => {
  assert.deepEqual(browserResult({ status: 202, data: { status: "queued" } }), { status: 202, body: { status: "queued" } });
  assert.equal(browserResult({ status: 401, data: null }).status, 502);
  assert.equal(browserResult({ status: 404, data: null }).status, 404);
  assert.equal(browserResult({ status: 429, data: null }).status, 429);
  assert.equal(browserResult({ status: 503, data: null }).status, 503);
  assert.equal(browserResult({ status: 500, data: { summary: "healthy" } }).status, 502);
  assert.equal(browserResult({ status: 500, data: { summary: "healthy" } }).body.summary, undefined);
});

test("every Crypty endpoint needs a signed-in user", async () => {
  const server = createApp({ acp: { url: "http://acp", tenant: "t", privateKey, allowed: new Set(["x"]) } }).listen(0);
  await new Promise((r) => server.once("listening", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    for (const [method, p] of [
      ["GET", "/api/crypty"],
      ["POST", "/api/crypty/diagnostics"],
      ["GET", "/api/crypty/tasks"],
      ["GET", `/api/crypty/tasks/${SUBJECT}`],
    ]) {
      const r = await fetch(base + p, { method });
      assert.equal(r.status, 401, `${method} ${p}`);
    }
  } finally {
    server.close();
  }
});
