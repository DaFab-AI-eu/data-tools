FROM dasi:0.2.8

USER root

RUN set -ex; \
    microdnf install -y curl tar findutils && \
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin && \
    pip install -q --no-cache-dir -U pip ruff

WORKDIR /tools
