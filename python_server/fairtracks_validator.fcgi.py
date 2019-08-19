#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

import libs.app

from flup.server.fcgi import WSGIServer

import configparser

# Creating the object holding the state of the API
if hasattr(sys, 'frozen'):
	basis = sys.executable
else:
	basis = sys.argv[0]

api_root = os.path.split(basis)[0]

# Setup tweaks
local_config = configparser.ConfigParser()
local_config.read(basis + '.ini')
app = libs.app.init_validator_app(local_config)

if __name__ == '__main__':
	WSGIServer(app).run()
