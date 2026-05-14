FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
RUN pip install --upgrade pip && pip install ".[dev]"


FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ripgrep git curl \
    && rm -rf /var/lib/apt/lists/*

# Tailwind CSS v4 standalone binary (no Node.js required)
RUN arch=$(dpkg --print-architecture) \
    && tw_arch=$([ "$arch" = "amd64" ] && echo "x64" || echo "$arch") \
    && curl -fsSL "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-${tw_arch}" \
       -o /usr/local/bin/tailwindcss \
    && chmod +x /usr/local/bin/tailwindcss

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

EXPOSE 8000

CMD ["bash", "scripts/start.sh"]
