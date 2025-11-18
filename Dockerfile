FROM python:3.10-slim

COPY requirements.txt .

RUN set -ex; \
    pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt
