# Model serving (Week 4, #94)

The cluster's LLM endpoint, on CPU: **Hermes (ACP worker) → LiteLLM → llama.cpp**. The model (Qwen2.5-0.5B-Instruct, Q4_K_M) is baked into the llama.cpp image built by `model-serving/Dockerfile` (#107), so nothing here downloads anything at runtime.

| File | What |
| --- | --- |
| `namespace.yaml` | `model-serving`, Pod Security **restricted** (enforced) |
| `model-serving-keys-sealed.yaml` | `LITELLM_MASTER_KEY` + `LLAMA_API_KEY`, sealed with the cluster cert |
| `networkpolicy.yaml` | default deny; DNS; LiteLLM → llama.cpp :8080; ACP worker → LiteLLM :4000 |
| `llama-cpp.yaml` | llama.cpp Deployment + Service (UID 10001, read-only root, 1–4 CPU, 512 Mi–1 Gi) |
| `litellm.yaml` | LiteLLM config, Deployment + Service (UID 65534, read-only root, upstream non-root image pinned by digest) |

## Who can call what

| Caller | Target | Allowed by | Key |
| --- | --- | --- | --- |
| Hermes (`agent-control-plane`, `acp-role: worker`) | LiteLLM `:4000` | `litellm-from-acp-worker` (+ an egress rule on the ACP side, step 3) | `LITELLM_MASTER_KEY` (Hermes gets it as `ACP_MODEL_API_KEY` in step 3) |
| LiteLLM | llama.cpp `:8080` | `llama-cpp-from-litellm` / `litellm-to-llama-cpp` | `LLAMA_API_KEY` |
| anything else | — | default deny | — |

Health endpoints (`/health` on llama.cpp; `/health/liveliness` and `/health/readiness` on LiteLLM) need no key, so kubelet probes work.

**No database, on purpose.** LiteLLM's per-client virtual keys, budgets and spend logs need PostgreSQL. With one client, the master key is enough for Week 4; per-client keys are a later improvement.

## Tested before merge (Docker, same images and settings)

Both containers ran read-only with all capabilities dropped, as their pod UIDs, on a Docker network **without internet**, using the LiteLLM config from `litellm.yaml`:

```
LiteLLM /health/liveliness, /health/readiness (no key) ... 200
LiteLLM /v1/models  no key / wrong key / master key ...... 401 / 400 / 200
LiteLLM chat completion with the master key .............. 'pong'  (model qwen2.5-0.5b-instruct)
llama.cpp /v1/*     no key / wrong key / right key ....... 401 / 401 / 200;  /health 200 without a key
memory after startup + one request ....................... llama.cpp ~200 MiB, LiteLLM ~955 MiB
```

Two things the tests caught, now noted in the manifests:

- llama-server reads its key from **`LLAMA_API_KEY`**. The `LLAMA_ARG_API_KEY` spelling is silently ignored and leaves the server open.
- `DISABLE_ADMIN_UI` has no effect in this LiteLLM version, so it isn't set. The UI pages are reachable only from Hermes, and every API call needs the master key.

## Rotating a key

```bash
# RUN ON: workstation (WSL), with the kubectl tunnel up
umask 077; D=~/.config/scc26-secrets
# edit $D/model-serving-keys-secret.yaml (new values), then:
kubeseal --cert $D/3ncryp3d-sealed-secrets.cert --format yaml \
  < $D/model-serving-keys-secret.yaml > gitops/resources/model-serving/model-serving-keys-sealed.yaml
# keep the sync-wave annotation, open a PR; after merge, restart both Deployments
# (and update acp-model if the master key changed)
```

## What follows

**Step 3 (separate PR): wire the ACP.**
- Set `ACP_MODEL=qwen2.5-0.5b-instruct` and `ACP_MODEL_BASE_URL` to `http://litellm.model-serving.svc.cluster.local:4000` (with or without `/v1`, per what Hermes expects).
- Seal `acp-model` (`ACP_MODEL_API_KEY` = the LiteLLM master key).
- Add the ACP egress rule worker → LiteLLM :4000.
- Scale Hermes `0 → 1`.
