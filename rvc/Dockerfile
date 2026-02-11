FROM alpine:3.19.1 as assets

RUN apk add \
      --update \
      --no-cache \
        bash \
        git \
        git-lfs\
        dos2unix

COPY --chmod=755 ./assets-download.sh /assets-download.sh

#convert malformed line endings if cloned from Windows
RUN dos2unix /assets-download.sh

RUN /assets-download.sh 88e42f0cb3662ddc0dd263a4814206ce96d53214 assets

FROM python:3.10.14-bullseye as app

SHELL [ "/bin/bash", "-c" ]

RUN apt update && \
    apt install -y \
      libsndfile1 \
      libsndfile1-dev && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=assets /assets /assets

WORKDIR /app

COPY ./pyproject.toml .

RUN pip install \
      --no-cache-dir \
      "poetry==1.7.1" && \
    poetry config virtualenvs.create false && \
    poetry install \
      --no-interaction \
      --no-root && \
    poetry cache clear --all .

COPY ./rvc ./rvc
COPY ./.env-docker ./.env

CMD [ "poetry", "run", "poe", "rvc-api" ]
