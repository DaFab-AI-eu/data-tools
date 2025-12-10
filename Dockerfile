FROM dasi:latest

WORKDIR /tmp

USER root

COPY requirements.txt .

COPY eodata-s3.creds /root/.aws/credentials

COPY pydafab /tmp/pydafab

RUN set -ex; \
    python -m pip install -q --no-cache-dir -r requirements.txt && \
    python -m pip install -q --no-cache-dir -e pydafab

USER $DEV_USERNAME

COPY eodata-s3.creds /home/$DEV_USERNAME/.aws/credentials

WORKDIR /workspace
