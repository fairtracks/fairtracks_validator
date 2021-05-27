#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

from flask import Flask, Blueprint
from flask_restx import Api, Namespace, Resource
from flask_cors import CORS
from flask_compress import Compress

from .ft_validator import FAIRTracksValidatorSingleton

from .res.ns import ROUTES as ROOT_ROUTES
from .res.schemas import ROUTES as SCHEMAS_ROUTES
from .res.validate import ROUTES as VALIDATE_ROUTES

ROUTE_SETS = [
	ROOT_ROUTES,
	SCHEMAS_ROUTES,
	VALIDATE_ROUTES
]

DEFAULT_MAX_FILE_SIZE_IN_MB = 16

def _register_ft_namespaces(api,res_kwargs):
	for route_set in ROUTE_SETS:
		ns = route_set['ns']
		api.add_namespace(ns,route_set['path'])
		for route in route_set['routes']:
			ns.add_resource(route[0],route[1],resource_class_kwargs=res_kwargs)

def init_validator_app(local_config):
	# This is the singleton instance shared by all the resources
	# This is done early, so it fails before setting all
	FTValidator = FAIRTracksValidatorSingleton(local_config)
	
	app = Flask('fairtracks_validator')
	
	# Setting up the temp upload folder size
	app.config['MAX_CONTENT_LENGTH'] = round(float(local_config.get('max_file_size',DEFAULT_MAX_FILE_SIZE_IN_MB)) * 1024 * 1024)
	app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
	
	blueprint = Blueprint('api','fairtracks_validator_api')
	#blueprint = Blueprint('api','fairtracks_validator_api',static_url_path='/',static_folder='static')
	
	# This enables CORS along all the app
	cors = CORS(app)
	
	# This enables compression
	compress = Compress(app)

	# Attaching the API to the app 
	api = Api(
		app=blueprint,
		version=FAIRTracksValidatorSingleton.APIVersion,
		title='FAIRification of Genomic Data Tracks JSON Schema validator REST API',
		description='This API allows validating JSON contents following JSON Schema defined at https://github.com/fairtracks/fairtracks_standard/',
		default='ftv',
		license='AGPL-3',
		default_label='FAIRtracks validator queries'
	)
	
	# This is the singleton instance shared by all the resources
	FTValidator.set_api_instance(api)
	
	res_kwargs = {'ftv': FTValidator}
	
	_register_ft_namespaces(api,res_kwargs)
	
	#app.register_blueprint(blueprint,url_prefix='/api')
	app.register_blueprint(blueprint,url_prefix='')
	
	return app
