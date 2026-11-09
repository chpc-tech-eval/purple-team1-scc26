# CPU model server (Week 4)

Builds the OCI image that serves our LLM endpoint on **CPU only**, resolving #94.

## Why this exists

Nyameko's guidance (Discord #purple-1, 2026-11-09): drop the bespoke single-GPU
dependency and serve through **LiteLLM → llama.cpp on CPU** now; the shared A100
gets wired in later via vLLM once it is online. The deliverable is "a small
open-weight model that fits our provisioning, demonstrated working" — not a large
model, not a GPU.

## What the image is

| | |
|---|---|
| Base | `ghcr.io/ggml-org/llama.cpp:server` — the upstream OpenAI-compatible server |
| Model | **Qwen2.5-0.5B-Instruct**, Q4_K_M GGUF (~0.4 GB), baked in at build time |
| Runtime egress | **none** — the model is in the image; the container needs no internet |
| Surface | `/health`, `/v1/models`, `/v1/chat/completions` on port 8080 |
| Registry | `ghcr.io/saxs-14/scc26-model-server:sha-<commit>` (published on merge to `dev`) |

The model is a build arg (`MODEL_REPO`/`MODEL_FILE`), so swapping to another tiny
GGUF is a one-line change. Qwen2.5-0.5B-Instruct is the default: small enough to be
fast on CPU, genuinely instruction-tuned, Apache-2.0 licensed.

## Reproducibility / pinning

The published **GHCR image digest** pins the runtime and the baked model together —
that digest is the deployable reference the gitops manifests use, exactly like the
platform image (#79/#100). The CI `model-image` workflow builds on every PR,
**smoke-tests that the baked model answers a prompt with no network** (`--network
none`), and pushes + reports the digest only on merge to `dev`.

## How it is deployed (follows this image)

1. **This image** lands first (Dockerfile + `model-image` CI). CI publishes the
   digest.
2. **Phase 1b — gitops** (`gitops/resources/model-serving/`, `student-platform`
   namespace): the llama.cpp Deployment+Service pinned to that digest, a **LiteLLM**
   proxy in front of it as the single OpenAI-style routing endpoint, default-deny +
   scoped NetworkPolicies, and an Argo `Application`.
3. **Phase 2 — wire the ACP**: point `acp-config` `ACP_MODEL` /
   `ACP_MODEL_BASE_URL` at the LiteLLM service, create the `acp-model` sealed
   secret, add a worker→LiteLLM egress NetworkPolicy, and scale Hermes `0→1`.

## Local check (optional)

```sh
docker build -t scc26-model-server model-serving/
docker run --rm --network none -p 8080:8080 scc26-model-server
curl -s localhost:8080/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5-0.5b-instruct","messages":[{"role":"user","content":"scary story in three words"}],"max_tokens":16}'
```
