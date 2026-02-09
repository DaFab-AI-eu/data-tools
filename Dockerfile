FROM dasi:0.2.8

USER root

WORKDIR /tmp

COPY ./pydafab ./pydafab

RUN set -ex; \
    cd pydafab && \
    pip install -q --no-cache-dir -U pip poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

WORKDIR /tools
