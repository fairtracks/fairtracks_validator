#!/bin/bash

set -e

SERVERPATH="$1"

apt-get update

# Needed in any case
apt-get -y install build-essential git

# This is only needed in Ubuntu images
#apt-get install python3-venv python3-dev

cd "$SERVERPATH"
python3 -m venv .pyRESTenv
source .pyRESTenv/bin/activate
pip install --no-cache-dir --upgrade pip
pip install --no-cache-dir -r requirements.txt -c constraints.txt
# Adding a default
cp fairtracks_validator.fcgi.py.yaml.template fairtracks_validator.fcgi.py.yaml
deactivate

# Last, cleanup
apt-get -y remove build-essential git
apt-get -y autoremove
rm -rf /var/lib/apt/lists/*
