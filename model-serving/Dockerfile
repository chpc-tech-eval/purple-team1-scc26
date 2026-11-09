# Week-4 CPU model server (#94 resolved: instructor said drop the bespoke A100
# dependency, use LiteLLM -> llama.cpp on CPU). The GGUF is baked into the image at
# BUILD time (CI has egress) so the RUNNING container needs ZERO internet egress and
# is fully reproducible: the published GHCR image digest pins model + runtime together.
#
# Tiny open-weight instruct model by design (instructor: "squeeze a tiny model on and
# demonstrate you understand how to deploy it" = success). Swap via build args.
ARG LLAMA_TAG=server
FROM ghcr.io/ggml-org/llama.cpp:${LLAMA_TAG}

# Default: Qwen2.5-0.5B-Instruct Q4_K_M (~400 MB) — small, fast on CPU, good instruct quality.
ARG MODEL_REPO=Qwen/Qwen2.5-0.5B-Instruct-GGUF
ARG MODEL_FILE=qwen2.5-0.5b-instruct-q4_k_m.gguf
ARG MODEL_ALIAS=qwen2.5-0.5b-instruct

USER root
RUN set -eux; \
    mkdir -p /models; \
    curl -fsSL "https://huggingface.co/${MODEL_REPO}/resolve/main/${MODEL_FILE}?download=true" -o /models/model.gguf; \
    test -s /models/model.gguf; \
    ls -l /models/model.gguf

ENV MODEL_ALIAS=${MODEL_ALIAS}
EXPOSE 8080

# The :server image's entrypoint is the llama.cpp OpenAI-compatible server (/llama-server).
# CPU-only, context 4096, 4 threads; serves /health, /v1/models, /v1/chat/completions.
ENTRYPOINT ["/llama-server"]
CMD ["-m", "/models/model.gguf", "--host", "0.0.0.0", "--port", "8080", "-a", "qwen2.5-0.5b-instruct", "-c", "4096", "-t", "4"]
