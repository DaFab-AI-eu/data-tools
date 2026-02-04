FROM dasi:0.2.8

USER root

RUN python -m pip install poetry

WORKDIR /tmp

COPY ./pydafab ./pydafab

RUN cd pydafab && poetry install

WORKDIR /tools
