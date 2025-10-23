FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml poetry.lock* requirements.txt* /app/

RUN set -eux; \
    if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    elif [ -f pyproject.toml ]; then \
      pip install --no-cache-dir poetry && \
      poetry export -f requirements.txt --output /tmp/requirements.txt --without-hashes && \
      pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi

COPY . /app

RUN pip install --no-cache-dir .

CMD ["python", "-m", "src"]
