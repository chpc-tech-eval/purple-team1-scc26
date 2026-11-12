# Week-4 CPU model server (#94 resolved: instructor said drop the bespoke A100
# dependency, use LiteLLM -> llama.cpp on CPU). The GGUF is baked into the image at
# BUILD time (CI has egress) so the RUNNING container needs ZERO internet egress and
# is fully reproducible: the published GHCR image digest pins model + runtime together.
#
# Tiny open-weight instruct model by design (instructor: "squeeze a tiny model on and
# demonstrate you understand how to deploy it" = success). Swap via build args.

# Base pinned by digest (like platform/Dockerfile): the :server tag is rebuilt upstream
# continuously, so the tag alone would make every build different.
ARG LLAMA_IMAGE=ghcr.io/ggml-org/llama.cpp:server@sha256:4d2de15a0ffbce704777c64026b40512a71e0bbc0b303a5fe5ea9bf71760dff9
FROM ${LLAMA_IMAGE}

# Default: Qwen2.5-0.5B-Instruct Q4_K_M (~490 MB, Apache-2.0): small, fast on CPU,
# good instruct quality. The model is pinned to a Hugging Face commit (not the moving
# `main` branch) and checked against its SHA-256, so a rebuild bakes exactly the same
# bytes or fails. To swap models, change the MODEL_* values together.
ARG MODEL_BASE_URL=https://huggingface.co
ARG MODEL_REPO=Qwen/Qwen2.5-0.5B-Instruct-GGUF
ARG MODEL_REVISION=9217f5db79a29953eb74d5343926648285ec7e67
ARG MODEL_FILE=qwen2.5-0.5b-instruct-q4_k_m.gguf
ARG MODEL_SHA256=74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db
ARG MODEL_ALIAS=qwen2.5-0.5b-instruct
# Same non-root UID as the other team workloads (runAsUser: 10001).
ARG APP_UID=10001

USER root
RUN set -eux; \
    mkdir -p /models; \
    curl -fsSL "${MODEL_BASE_URL}/${MODEL_REPO}/resolve/${MODEL_REVISION}/${MODEL_FILE}" -o /models/model.gguf; \
    echo "${MODEL_SHA256}  /models/model.gguf" | sha256sum -c -; \
    chmod 0444 /models/model.gguf; \
    ls -l /models/model.gguf

# llama-server reads its flags from LLAMA_ARG_* variables, so the served model name
# follows MODEL_ALIAS and the Deployment can override any of them without a new image.
# CPU-only, context 4096, 4 threads (match the pod's CPU limit).
# Serves /health, /v1/models, /v1/chat/completions on port 8080.
ENV LLAMA_ARG_MODEL=/models/model.gguf \
    LLAMA_ARG_ALIAS=${MODEL_ALIAS} \
    LLAMA_ARG_HOST=0.0.0.0 \
    LLAMA_ARG_PORT=8080 \
    LLAMA_ARG_CTX_SIZE=4096 \
    LLAMA_ARG_THREADS=4
EXPOSE 8080

# Drop root: the model file is read-only and world-readable; nothing else is written.
USER ${APP_UID}:${APP_UID}

# The :server image's ENTRYPOINT launches llama-server; all flags come from ENV.
CMD []
