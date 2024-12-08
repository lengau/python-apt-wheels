#!/bin/bash

cd /tmp

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get source python-apt
cd python-apt-*

export GLIBC_VERSION="$(ldd --version | grep GLIBC | cut -d' ' -f4 | cut -d- -f1 | tr . _)"
export DEBVER="$(apt-cache show python3-apt|grep Version | head -n 1|cut -d' ' -f2)"

python3 setup.py bdist_wheel --dist-dir /github/workspace --plat-name "manylinux_$GLIBC_VERSION_$(uname -m)"
