// Crypty: the platform's server-side client for the Agent Control Plane (week4 §3).
//
// The browser never sees the signing key, the assertion or ACP itself. For every
// call the backend signs a fresh, short-lived EdDSA assertion (at most 60 s; ACP
// rejects anything over 90 s) for the signed-in user, then calls ACP inside the
// cluster. Claims follow ACP's verifier (nyameko/agent-control-plane auth.py).
import crypto from "node:crypto";
import fs from "node:fs";

export const ACP_ISSUER = "quantum-platform";
export const ACP_AUDIENCE = "agent-control-plane";
export const ACP_SCOPE = "admin:diagnostics";
// Fixed by ACP's schema (CHECK constraint): the one allowed read-only diagnostic.
export const ACP_DIAGNOSTIC = "quantum-platform-pod-readiness";
export const MAX_LIFETIME_SECONDS = 60;
const MAX_RESPONSE_BYTES = 1_000_000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const isUuid = (value) => typeof value === "string" && UUID.test(value);
const b64url = (value) => Buffer.from(value).toString("base64url");

export function signAssertion({
  subjectUuid,
  tenant,
  privateKey,
  now = Math.floor(Date.now() / 1000),
  lifetime = MAX_LIFETIME_SECONDS,
  jti = crypto.randomUUID(),
}) {
  if (!isUuid(subjectUuid)) throw new Error("subject must be a UUID");
  if (!tenant) throw new Error("tenant required");
  if (!Number.isInteger(lifetime) || lifetime < 1 || lifetime > MAX_LIFETIME_SECONDS) {
    throw new Error(`lifetime must be 1-${MAX_LIFETIME_SECONDS} seconds`);
  }
  const header = b64url(JSON.stringify({ alg: "EdDSA", typ: "JWT" }));
  const payload = b64url(
    JSON.stringify({
      iss: ACP_ISSUER,
      aud: ACP_AUDIENCE,
      sub: `urn:quantum-platform:user:${subjectUuid}`,
      tenant,
      scope: ACP_SCOPE,
      iat: now,
      nbf: now,
      exp: now + lifetime,
      jti,
    }),
  );
  const signature = crypto.sign(null, Buffer.from(`${header}.${payload}`), privateKey);
  return `${header}.${payload}.${b64url(signature)}`;
}

// Configuration from the Deployment. Returns null when Crypty is not configured
// (the page then says so); throws on a present-but-invalid key, so a broken
// mount fails loudly at start-up instead of producing unsigned calls.
export function acpConfig(env = process.env) {
  const { ACP_URL: url, ACP_SIGNING_KEY_FILE: keyFile, ACP_TENANT_ID: tenant } = env;
  if (!url || !keyFile || !tenant) return null;
  const parsed = new URL(url);
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password || parsed.search) {
    throw new Error("ACP_URL must be a plain http(s) URL without credentials or query");
  }
  const privateKey = crypto.createPrivateKey(fs.readFileSync(keyFile));
  if (privateKey.asymmetricKeyType !== "ed25519") throw new Error("ACP signing key must be Ed25519");
  const allowed = new Set(
    (env.ACP_ALLOWED_USERS || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
  return {
    url: url.replace(/\/+$/, ""),
    tenant,
    privateKey,
    allowed,
    model: env.ACP_MODEL_LABEL || "",
  };
}

// One call to ACP as the given user. Never follows redirects, bounded time and size.
export async function acpRequest(cfg, user, method, path, { body, idempotencyKey, fetchImpl = fetch, timeoutMs = 10_000 } = {}) {
  const token = signAssertion({ subjectUuid: user.agent_principal, tenant: cfg.tenant, privateKey: cfg.privateKey });
  const headers = { authorization: `Bearer ${token}`, accept: "application/json" };
  if (body !== undefined) headers["content-type"] = "application/json";
  if (idempotencyKey) headers["idempotency-key"] = idempotencyKey;
  const response = await fetchImpl(`${cfg.url}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    redirect: "error",
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  if (text.length > MAX_RESPONSE_BYTES) throw new Error("ACP response too large");
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  return { status: response.status, data };
}

// Map ACP's answer to what the browser may see. Failures stay failures; nothing
// is ever turned into a "healthy" result here.
export function browserResult({ status, data }) {
  if (status === 200 || status === 202) return { status, body: data };
  if (status === 401) return { status: 502, body: { error: "ACP rejected the platform's signed request" } };
  if (status === 404) return { status: 404, body: { error: "task not found" } };
  if (status === 429) return { status: 429, body: { error: "a diagnostic is already running; try again shortly" } };
  if (status === 503) return { status: 503, body: { error: "ACP task store unavailable" } };
  return { status: 502, body: { error: `unexpected ACP response (${status})` } };
}
