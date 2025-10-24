# Build the release image by cloning the learn-caesar-cipher repository on the fly.
# This keeps the CI/CD automation repo clean while always pulling the latest cipher sources.

FROM python:3.12-slim AS builder
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace

# Install git so we can clone external repositories during the build.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Clone the Caesar cipher teaching project from GitHub.
RUN git clone --depth 1 https://github.com/jguida941/learn-caesar-cipher.git /workspace/learn-caesar-cipher
WORKDIR /workspace/learn-caesar-cipher/caesar_cli

# Install dependencies if available.
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    elif [ -f pyproject.toml ]; then \
        pip install --no-cache-dir .; \
    else \
        echo "No installable metadata found; skipping dependency install"; \
    fi

WORKDIR /workspace/learn-caesar-cipher

FROM python:3.12-slim
WORKDIR /app

# Copy the freshly cloned project plus the CI/CD plan documentation into the runtime image.
COPY --from=builder /workspace/learn-caesar-cipher /app/learn-caesar-cipher
COPY plan.md /app/plan.md
COPY docs /app/docs

# Default command: print confirmation that the plan + project were bundled.
CMD ["python", "-c", "print('CI/CD plan bundled with learn-caesar-cipher from GitHub')"]
