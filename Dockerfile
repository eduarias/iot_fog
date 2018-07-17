FROM python:2.7.15-alpine3.8

RUN apk add --update \
    git \
    python-dev \
    build-base \
  && rm -rf /var/cache/apk/*

RUN mkdir /cloud_connector
COPY requirements.txt .
RUN pip install -r /requirements.txt
COPY ./cloud_connector /cloud_connector

WORKDIR /cloud_connector

CMD ["python", "/cloud_connector/cloud_connector.py"]