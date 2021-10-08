#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os
import logging

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

#print(f"JAO {os.environ.get('WERKZEUG_RUN_MAIN')}", file=sys.stderr)
#sys.stderr.flush()
app, ftv = libs.app.init_validator_app(local_config)

DEFAULT_LOGGING_FORMAT = '%(asctime)-15s - [%(process)d][%(levelname)s] %(message)s'

if __name__ == '__main__':
	if len(sys.argv) > 1:
		# This verb is used to shut down existing instances
		# from command-line
		if sys.argv[1] == 'shutdown':
			ftv.shutdown()
		
		host = local_config.get('host', "0.0.0.0")
		port = local_config.get('port', 5000)
		debug = sys.argv[1] != 'standalone'
		if debug:
			logLevel = logging.DEBUG
			# Let's suppose it's a numerical port
			try:
				port = int(sys.argv[1])
			except ValueError:
				pass
			
			# Debug mode should be tied only to localhost
			host = "127.0.0.1"
		else:
			logLevel = logging.INFO
		
		loggingConfig = {
			'level': logLevel,
			'format': DEFAULT_LOGGING_FORMAT,
		#	'filename': 'debug-traces.txt',
		}
		logging.basicConfig(**loggingConfig)

		app.run(debug=debug, port=port, host=host, threaded=False, processes=1)
	else:
		loggingConfig = {
			'level': logging.ERROR,
			'format': DEFAULT_LOGGING_FORMAT,
		#	'filename': 'debug-traces.txt',
		}
		logging.basicConfig(**loggingConfig)
		from flup.server.fcgi import WSGIServer

		WSGIServer(app).run()
