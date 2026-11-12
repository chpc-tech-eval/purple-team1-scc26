# Optional: step up to Qwen2.5-1.5B (prepared, not deployed)

> **Status: OPTIONAL, NOT BUILT, NOT DEPLOYED, NOT TESTED.** This folder shows that the Week-4 model route can step up to a stronger model by changing files in Git, without code changes. Nothing here runs:
>
> - Argo CD does not read `gitops/optional/` (the root app reads `gitops/applications/`; `model-serving` reads `gitops/resources/model-serving/`).
> - It is outside `model-serving/**`, so it does not trigger the `model-image` workflow.
>
> The live default stays **`qwen2.5-0.5b-instruct`**. Do the steps below later, only if the team decides to.

## Why

The 0.5B model passes the Week-4 bar (a tiny model deployed and understood), and the full chain works end to end ([Week-4 evidence](../../../evidence/week4/README.md)). Its explanations show the size limit: Crypty run `61898af2` contradicts itself ("3 out of the 3 pods are not ready"), and the three-word test went 0/3 ([demo manifest](../../../evidence/runs/20261112T122709Z-week4-model-serving-live-demo.json)). Qwen2.5-1.5B-Instruct is the next step up that still fits on CPU. It is the same family, licence (Apache-2.0) and quantisation (Q4_K_M), and about 1.1 GB instead of 0.5 GB.

The A100 (vLLM) is a separate, later option. It plugs into the same place: one more LiteLLM backend, then switch `ACP_MODEL`.

## What's here

| File | What it is |
| --- | --- |
| [`build-args.env`](build-args.env) | `MODEL_*` build arguments for the existing `model-serving/Dockerfile`: Hugging Face commit and SHA-256 pinned, so the build is reproducible or fails |
| [`llama-cpp-qwen2.5-1.5b.yaml`](llama-cpp-qwen2.5-1.5b.yaml) | A second llama.cpp Deployment and Service with their own name and label, 3 GiB memory limit, and the two NetworkPolicies (LiteLLM ↔ this server only). The image is a deliberately invalid placeholder until step 1 is done |

## Design: next to the 0.5B, not instead of it

```
ACP worker (Hermes) ──ACP_MODEL──▶ LiteLLM ─┬─▶ llama-cpp              qwen2.5-0.5b-instruct  (live default)
                                            └─▶ llama-cpp-qwen2-5-1-5b qwen2.5-1.5b-instruct  (optional)
```

Both models stay available behind the one LiteLLM endpoint and master key. The ACP uses whichever model `ACP_MODEL` names, every run records it, and switching back is a one-line PR.

## Steps to enable it later (each one a reviewed PR)

**1. Build the image (CI).** The `model-image` workflow builds only the default today. Give it a way to pass build arguments and tag the result separately. For example, add a `workflow_dispatch` input `variant` (`default` | `qwen2.5-1.5b`). When it's set, append `--build-arg` for each line of `build-args.env` and tag `sha-<12>-qwen2.5-1.5b`. The existing smoke test then checks the 1.5B the same way: no network, non-root, and `/v1/models` reads back `qwen2.5-1.5b-instruct`. Note: changing the workflow or `model-serving/**` on `dev` also rebuilds and pushes the default 0.5B image under a new tag. That's harmless, because the cluster pins by digest.

**2. Deploy it next to the 0.5B (GitOps).**
- Copy `llama-cpp-qwen2.5-1.5b.yaml` into `gitops/resources/model-serving/`, with the digest from step 1 in place of the placeholder.
- In `litellm.yaml`, add a second `model_list` entry and an env var on the LiteLLM Deployment:

  ```yaml
  # litellm-config, under model_list:
  - model_name: qwen2.5-1.5b-instruct
    litellm_params:
      model: openai/qwen2.5-1.5b-instruct
      api_base: os.environ/LLAMA_1_5B_API_BASE
      api_key: os.environ/LLAMA_API_KEY
      timeout: 170
  # litellm Deployment, container env:
  - name: LLAMA_1_5B_API_BASE
    value: http://llama-cpp-qwen2-5-1-5b.model-serving.svc.cluster.local:8080/v1
  ```
- A ConfigMap change doesn't restart LiteLLM. Bump a pod-template annotation on the LiteLLM Deployment in the same PR, as #119 did for the worker.
- Check after sync: both llama.cpp pods are Ready. Then call LiteLLM `/v1/models` with the master key, through a port-forward as in the [model-serving README](../../resources/model-serving/README.md). It should list both names. The 0.5B demo must still pass.

**3. Switch the agent (GitOps, one line plus a restart).** In `gitops/resources/agent-control-plane/configmap.yaml` set `ACP_MODEL: qwen2.5-1.5b-instruct`, and bump `purple-team1/worker-patch-revision` in `hermes.yaml` so the worker restarts with it.

**4. Measure and record.** Run Crypty from the Student Platform a few times. Record a manifest (`scripts/provenance/write_manifest.py`) with:
- run time (the budget is `ACP_RUN_TIMEOUT_SECONDS` = 180 s)
- llama.cpp tokens and `truncated`
- `kubectl top pod` memory
- explanation quality against the evidence
- the three-word test

Compare with the 0.5B runs. Keep the 1.5B only if it's clearly better and within budget.

**Roll back:** set `ACP_MODEL` back to `qwen2.5-0.5b-instruct` and bump the annotation. The 0.5B server was never removed.

## Things to check (known, not yet measured)

- **Hermes' 64K context check.** Through LiteLLM, Hermes can't read the real context size, so it guesses from the model name: names containing "qwen" resolve to 131,072, which passes. `qwen2.5-1.5b-instruct` passes for the same reason as the 0.5B. A model from another family (Llama, Phi, …) must be tested first, or Hermes may refuse it. See [ACP README](../../resources/agent-control-plane/README.md).
- **Speed on CPU.** Expect roughly 2–3× slower generation than 0.5B on the same 4 threads. The 0.5B runs took 16–18 s, so this should fit the 180 s budget, but it's an estimate until step 4.
- **Memory.** The 3 GiB limit is a cautious guess (1.1 GB model + 4K KV cache + buffers). Measure, then tighten.
- **Context stays 4,096** (`LLAMA_ARG_CTX_SIZE` in the image). Crypty's prompt used 993 tokens, so there's room.
- **Security is unchanged:** same key, same non-root/read-only pod, egress still only LiteLLM ↔ llama.cpp. The worker can still reach only LiteLLM ([worker security checks](../../../evidence/runs/20261112T180840Z-week4-acp-worker-security-checks.json)).
