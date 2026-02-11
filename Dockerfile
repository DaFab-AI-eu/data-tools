FROM dasi:0.2.8

USER root

WORKDIR /tmp

COPY ./pydafab ./pydafab

RUN set -ex; \
    pip install -q --no-cache-dir -U pip poetry && \
    cd pydafab && \
    pip install -q -e /tmp/pydafab 
    # poetry config virtualenvs.create false && \
    # poetry install --no-interaction --no-ansi

WORKDIR /tools
