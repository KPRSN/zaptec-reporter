# Install UV.
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /uvx /bin/

# Change working directory.
WORKDIR /app

# Enable bytecode compilation.
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking.
ENV UV_LINK_MODE=copy

# Install dependencies.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-editable

# Install the rest of the project.
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

# Place executable in path and set the entrypoint.
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["zaptec-reporter"]

# Run the application with default args.
CMD ["-h"]
