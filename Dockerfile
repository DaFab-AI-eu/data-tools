ARG DASI_IMAGE=ghcr.io/dafab-ai-eu/dasi:0.3.1
FROM ${DASI_IMAGE} AS package

USER root

WORKDIR /tmp

COPY ./pydafab ./pydafab

RUN set -ex; \
    pip install -q --no-cache-dir -U pip && \
    cd pydafab && \
    pip install -q -e /tmp/pydafab


COPY ./copernicus /tools/copernicus

FROM package AS test

RUN pip install -q --no-cache-dir -r /tmp/pydafab/requirements-dev.txt

WORKDIR /tmp/pydafab

CMD ["pytest", "-q", "tests"]

FROM package AS runtime

WORKDIR /tools
