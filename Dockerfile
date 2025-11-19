FROM dasi:latest

WORKDIR /tmp

COPY requirements.txt .

USER root

RUN set -ex; \
    python -m pip install -q --no-cache-dir -r requirements.txt

USER $DEV_USERNAME

WORKDIR /workspace
