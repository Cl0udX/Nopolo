#!/usr/bin/env bash
#
# Runs RVC API in Docker.

set -e

tag="rvc"

docker build -t "${tag}" .

docker run -it \
  -p 8000:8000 \
  -v "${PWD}/assets/weights:/weights:ro" \
  -v "${PWD}/assets/indices:/indices:ro" \
  -v "${PWD}/assets/audios:/audios:ro" \
  "${tag}"
