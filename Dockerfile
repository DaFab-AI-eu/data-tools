FROM dasi:latest

WORKDIR /tmp

COPY requirements.txt .

RUN set -ex; \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /tmp/*
