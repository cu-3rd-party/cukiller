#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for example_file in "${script_dir}"/*.example; do
  target_file="${example_file%.example}"
  cp "${example_file}" "${target_file}"
done
