FROM dasi:latest

USER root

WORKDIR /tmp

COPY requirements.txt ./requirements.txt
COPY pydafab ./pydafab

RUN set -ex; \
    python -m pip install -q --no-cache-dir -r ./requirements.txt && \
    python -m pip install -q --no-cache-dir -e ./pydafab

WORKDIR /tools
