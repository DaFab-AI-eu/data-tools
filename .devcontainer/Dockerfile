FROM dasi-test:latest

USER root

RUN set -ex; \
    pip install -q --no-cache-dir -U pip poetry && \
    pip install -q --no-cache-dir -e /workspace/dasi/pydasi

WORKDIR /tools
