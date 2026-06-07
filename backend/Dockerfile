FROM python:3.12-slim

WORKDIR /app

# Install curl for Tectonic download
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Tectonic (static musl binary — x86_64 only)
RUN curl -fsSL \
    https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-unknown-linux-musl.tar.gz \
    | tar xz -C /usr/local/bin \
    && chmod +x /usr/local/bin/tectonic

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
