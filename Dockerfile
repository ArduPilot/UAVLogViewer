# syntax=docker/dockerfile:1

# ---- Build stage: install dependencies and compile the static site ----
FROM node:24-trixie-slim AS build

# git is needed for the submodules and the build commit hash
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates=20250419 \
        git=1:2.47.3-0+deb13u1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Copy package manifests and the patch-package patches applied on postinstall
COPY package.json package-lock.json ./
COPY patches ./patches

# Install dependencies and update browserslist database
RUN npm ci && \
    npx --yes update-browserslist-db@latest

# Copy only what the build needs (.git and .gitmodules for submodules and the commit hash)
COPY .git ./.git
COPY build ./build
COPY config ./config
COPY src ./src
COPY static ./static
COPY .gitmodules .eslintignore .eslintrc.cjs .postcssrc.js babel.config.cjs index.html ./

# Initialise submodules only if .gitmodules exists (network required),
# build production assets and drop the dev dependencies
RUN if [ -f .gitmodules ]; then \
        git submodule update --init; \
    fi && \
    npm run build && \
    npm prune --omit=dev

# ---- Runtime stage: serve the built files as a non-root user ----
FROM node:24-trixie-slim

# Allow overriding UID/GID for rootless Podman (--userns=keep-id)
ARG USER_UID=1000
ARG USER_GID=1000

# The base image already has a "node" user/group with UID/GID 1000, so drop it first
RUN userdel node && \
    rm -rf /home/node && \
    if getent group node > /dev/null; then groupdel node; fi && \
    groupadd --gid "${USER_GID}" nodeuser && \
    useradd -l --uid "${USER_UID}" --gid "${USER_GID}" --create-home nodeuser

WORKDIR /usr/src/app

# Application files stay owned by root so the app user cannot modify them
COPY --from=build --chmod=644 /usr/src/app/package.json ./
COPY --from=build /usr/src/app/node_modules ./node_modules
COPY --from=build /usr/src/app/dist ./dist
# Static server config: serves a terrain tileset mounted at dist/quantized as gzip
COPY --chmod=644 serve.json ./

USER ${USER_UID}:${USER_GID}

EXPOSE 8080
CMD ["npm", "start"]
