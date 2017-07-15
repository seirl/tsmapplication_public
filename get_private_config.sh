#!/bin/bash

set -e

extract_dir=$( mktemp -d )
pushd "$extract_dir"

curl -O https://www.tradeskillmaster.com/download/setup.exe
7z -y x setup.exe 2>/dev/null >/dev/null || true
popd

uncompyle6 "$extract_dir/PrivateConfig.pyc" > src/PrivateConfig.py

rm -rf "$extract_dir"
