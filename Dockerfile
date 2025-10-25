ARG PYTHON_IMAGE="python:3.12-slim@sha256:e97cf9a2e84d604941d9902f00616db7466ff302af4b1c3c67fb7c522efa8ed9"
ARG CAESAR_SHA="fafa48a782121ec93325ddba92ee71e85ae04cd6"

FROM ${PYTHON_IMAGE} AS builder
ARG CAESAR_SHA
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /workspace

# Install curl for downloading the Caesar project archive.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Fetch the Caesar cipher project at a fixed commit to guarantee hermetic builds.
RUN bash -o pipefail -c '\
    set -euo pipefail; \
    curl -fsSL "https://github.com/jguida941/learn-caesar-cipher/archive/${CAESAR_SHA}.tar.gz" \
      | tar -xz -C /workspace; \
    if [[ ! -d "/workspace/learn-caesar-cipher-${CAESAR_SHA}" ]]; then \
      echo "Failed to locate extracted project for commit ${CAESAR_SHA}"; \
      exit 1; \
    fi; \
    mv "/workspace/learn-caesar-cipher-${CAESAR_SHA}" /workspace/learn-caesar-cipher \
  '

WORKDIR /workspace/learn-caesar-cipher/caesar_cli

# Install dependencies using a pinned pip toolchain.
RUN python -m pip install --upgrade pip==24.2 \
    && if [ -f requirements.txt ]; then \
         python -m pip install --no-cache-dir -r requirements.txt; \
       elif [ -f pyproject.toml ]; then \
         python -m pip install --no-cache-dir .; \
       else \
         echo "No installable metadata found; skipping dependency install"; \
       fi

WORKDIR /workspace/learn-caesar-cipher

FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Copy the freshly cloned project plus the CI/CD plan documentation into the runtime image.
COPY --from=builder /workspace/learn-caesar-cipher /app/learn-caesar-cipher
COPY plan.md /app/plan.md
COPY docs /app/docs

# Default command: print confirmation that the plan + project were bundled.
CMD ["python", "-c", "print('CI/CD plan bundled with learn-caesar-cipher from GitHub')"]
