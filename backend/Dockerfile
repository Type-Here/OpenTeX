FROM python:3.12-slim

# TARGETARCH is set automatically by Docker buildx: "amd64" on x86_64, "arm64" on M-series Macs.
ARG TARGETARCH

WORKDIR /app

# Install curl for Tectonic download
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Tectonic — pick the native musl binary for the build architecture so
# the compiler runs without Rosetta 2 / QEMU emulation on Apple Silicon.
RUN ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
    curl -fsSL \
    "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-${ARCH}-unknown-linux-musl.tar.gz" \
    | tar xz -C /usr/local/bin \
    && chmod +x /usr/local/bin/tectonic

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
