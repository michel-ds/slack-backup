#!/bin/sh
export TOKEN='xoxp-4...'  # Bot User OAuth Token
# Optional settings: (you can omit them)
#export FILE_TOKEN='xoxe-...'  # file access export token from previous step
export DOWNLOAD=1  # download all message files locally too
export STORAGE_LOC='<S£ BUCKET>'
export PROFILE='<AWS PROFILE or unset>'
python lambda_function.py