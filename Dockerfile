FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY app /app/app
COPY scripts /app/scripts

ARG TORCH_INDEX_URL=""
RUN if [ -n "$TORCH_INDEX_URL" ]; then \
      PIP_EXTRA_INDEX_URL="$TORCH_INDEX_URL" pip install --no-cache-dir -e ".[s3,postgres,redis]"; \
    else \
      pip install --no-cache-dir -e ".[s3,postgres,redis]"; \
    fi

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
