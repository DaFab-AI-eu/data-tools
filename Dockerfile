ARG DASI_IMAGE=ghcr.io/dafab-ai-eu/dasi:0.3.2
FROM ${DASI_IMAGE} AS package

USER root

WORKDIR /tmp

COPY ./pydafab ./pydafab

RUN set -ex; \
    pip install -q --no-cache-dir -U pip && \
    cd pydafab && \
    pip install -q -e /tmp/pydafab


COPY ./copernicus /tools/copernicus

# Index keys up to 64 characters: S1 field keys such as schema-calibration-iw1-vh:application_xml
# overflow FDB's default 32. Only writers need this; each index records its own type for readers.
ENV FDB_INDEX_TYPE=BTreeIndex64

FROM package AS test

RUN pip install -q --no-cache-dir -r /tmp/pydafab/requirements-dev.txt

WORKDIR /tmp/pydafab

CMD ["pytest", "-q", "tests"]

FROM package AS runtime

WORKDIR /tools
