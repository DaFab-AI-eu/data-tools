FROM dasi:0.2.8

USER root

WORKDIR /tmp

COPY ./requirements.txt ./requirements.txt

RUN python -m pip install -q --no-cache-dir -r ./requirements.txt

WORKDIR /tools
