#!/usr/bin/env bash
#
# Runs request to RVC API on localhost.

set -e

host="http://127.0.0.1:8000"

url="${host}/inference"

url+="?res_type=json"

model_path=""
index_path=""
input_audio=""
output_audio_suffix=""

while [ $# -gt 0 ]; do
  if [ "$1" == "--model_path" ]; then
    model_path="$2"
  elif [ "$1" == "--index_file" ]; then
    index_path="$2"
  elif [ "$1" == "--input_audio" ]; then
    input_audio="$2"
  else
    arg_name="${1#--}"
    arg_value="$2"

    url+="&${arg_name}=${arg_value}"
    output_audio_suffix+="-${arg_name}_${arg_value}"
  fi

  shift
  shift
done

model_path_base="$(basename "${model_path}")"
model_path_base_without_ext="${model_path_base%.*}"
index_path_base="$(basename "${index_path}")"
input_audio_base="$(basename "${input_audio}")"
input_audio_dirname="$(dirname "${input_audio}")"
output_audio_base_without_ext="${input_audio_base%.*}"
output_audio="${input_audio_dirname}/${output_audio_base_without_ext}-${model_path_base_without_ext}${output_audio_suffix}.wav"

cp "${model_path}" "./assets/weights/${model_path_base}"
cp "${input_audio}" "./assets/audios/${input_audio_base}"

if [ -f "${index_path}" ]; then
  url+="&index_file=${index_path_base}"
  cp "${index_path}" "./assets/indices/${index_path_base}"
fi

curl -X "POST" "${url}" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "modelpath=${model_path_base}" \
  -F "input_audio=/audios/${input_audio_base}" \
| jq -r '.audio' \
| base64 -d > "${output_audio}"
