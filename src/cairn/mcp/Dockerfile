# syntax=docker/dockerfile:1

# ---------- Stage 1: build the virtualenv ----------
FROM python:3.12-slim-bookworm AS builder

# Pin uv to a specific version. (The ghcr `uv` image only publishes
# pinned-version tags for the standalone binary, not for the combined
# Python+uv variants, so we copy the binary into a regular python base.)
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CAIRN=0.0.0+docker \
    HATCH_VCS_PRETEND_VERSION=0.0.0+docker

WORKDIR /app

# Install dependencies *without* the project itself. This layer caches
# unless uv.lock or pyproject.toml change, so src/ edits rebuild fast.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --extra mcp

# Copy the project and install it into the existing venv.
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra mcp --no-editable

# ---------- Stage 2: minimal runtime ----------
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 cairn \
    && useradd  --uid 1000 --gid cairn --create-home --shell /usr/sbin/nologin cairn

WORKDIR /app
COPY --from=builder --chown=cairn:cairn /app /app

ENV PATH="/app/.venv/bin:${PATH}"
USER cairn

EXPOSE 8765

CMD ["cairn", "mcp", \
     "--transport", "streamable-http", \
     "--host", "0.0.0.0", \
     "--port", "8765", \
     "--path", "/mcp"]
