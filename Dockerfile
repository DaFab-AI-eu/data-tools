FROM dasi:0.2.8

USER root

WORKDIR /tmp

COPY ./pydafab ./pydafab

RUN set -ex; \
    pip install -q --no-cache-dir -U pip && \
    cd pydafab && \
    pip install -q -e /tmp/pydafab


COPY ./copernicus /tools/copernicus

WORKDIR /tools
