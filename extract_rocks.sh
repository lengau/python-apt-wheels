#!/bin/bash

set -euo pipefail

function extract_rock(){
  rock="$1"

  if [[ ! -f "${rock}" ]]; then
    echo "File does not exist: ${rock}" >> /dev/stderr
    exit 64
  fi
  echo "Extracting rock ${rock}..."

  tempdir="$(mktemp -d extracted-$(basename ${rock})-XXXXX)"
  echo $tempdir

  skopeo copy "oci-archive:${rock}" "oci:${tempdir}"

  for blob in "${tempdir}/blobs/sha256/"*; do
    tar zxf "${blob}" -C "${tempdir}" || true
  done

  mv "${tempdir}/"*.whl .

  rm -rf "${tempdir}"
}

for rock in "$@"; do
  extract_rock "${rock}"
done
