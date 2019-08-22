#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

import libs.app

import yaml
# We have preference for the C based loader and dumper, but the code
# should fallback to default implementations when C ones are not present
try:
	from yaml import CLoader as YAMLLoader, CDumper as YAMLDumper
except ImportError:
	from yaml import Loader as YAMLLoader, Dumper as YAMLDumper

# Creating the object holding the state of the API
if hasattr(sys, 'frozen'):
	basis = sys.executable
else:
	basis = sys.argv[0]

api_root = os.path.split(basis)[0]

# Setup tweaks
config_file = basis + '.yaml'
with open(config_file,"r",encoding="utf-8") as cf:
	local_config = yaml.load(cf,Loader=YAMLLoader)

app = libs.app.init_validator_app(local_config)

if __name__ == '__main__':
	port = int(sys.argv[1])  if len(sys.argv) > 1  else 5000
	app.run(debug=True,port=port)
