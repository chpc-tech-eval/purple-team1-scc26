# SCC26 Student Project Platform: one image, built by GitHub Actions (week3 §11).
# Stage 1 builds the static Astro site; stage 2 runs the API as a non-root user.
# No credentials are baked in: they arrive as Kubernetes env from SealedSecrets.

FROM docker.io/library/node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npx astro build

FROM docker.io/library/node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20
ENV NODE_ENV=production PORT=8080 STATIC_DIR=/app/public
WORKDIR /app
COPY api/package.json api/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force
COPY api/src ./src
COPY --from=frontend /src/dist ./public
ARG GIT_SHA=unknown
ARG APP_VERSION=dev
ENV GIT_SHA=$GIT_SHA APP_VERSION=$APP_VERSION
USER 1000
EXPOSE 8080
CMD ["node", "src/server.js"]
