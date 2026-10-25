# SCC26 Student Project Platform: one image, built by GitHub Actions (week3 §11).
# Stage 1 builds the static Astro site; stage 2 runs the API as a non-root user.
# No credentials are baked in: they arrive as Kubernetes env from SealedSecrets.

FROM docker.io/library/node:22.21.1-bookworm-slim@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npx astro build

FROM docker.io/library/node:22.21.1-bookworm-slim@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c
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
