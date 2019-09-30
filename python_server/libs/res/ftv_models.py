#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

import werkzeug
from flask_restplus import Namespace, Api, Resource, fields, reqparse

class FTVResource(Resource):
	'''This class eases passing the instance of the validator API'''
	def __init__(self,api=None,*args,**kwargs):
		super().__init__(api,*args,**kwargs)
		self.ftv = kwargs['ftv']



NS = Namespace('ftv','FAIRtracks REST validator')

config_model = NS.model('FTVConfig', {
	'schemas': fields.List(fields.String, required=True, description='The schema URLs in the configuration file')
})

ftv_info_model = NS.model('FTVInfo', {
	'version': fields.String(required=True, description = 'API Version'),
	'config': fields.Nested(config_model, required=True, description = 'Public configuration bits')
})

########################
# The different models #
########################
SCHEMAS_NS = Namespace('schemas','Schemas being used for validation')

wci = fields.Wildcard(fields.Raw)

schema_error_model = SCHEMAS_NS.model('SchemaError', {
	'*': wci
})

# Lesson learned: fields.Url is for self generated URIs
schema_info_model = SCHEMAS_NS.model('SchemaInfo', {
	'source_urls': fields.List(fields.String,required=True, description = 'URL location of the JSON Schema'),
	'fetched_at': fields.DateTime,
	'errors': fields.List(fields.Nested(schema_error_model),required=False, description = 'The list of detected errors when the JSON Schema was initially processed'),
	'schema_hash': fields.String(required=False, description = 'The SHA1 hash of the normalized JSON Schema, in hexadecima representation'),
	'schema_id': fields.String(required=False, description = 'The id of the schema'),
})

#schema_info_model_schema = SCHEMAS_NS.schema_model('SchemaInfo', {
#})


wcs = fields.Wildcard(fields.Raw)
schema_source_model = SCHEMAS_NS.model('SchemaSource', {
	'*': wcs
})

#schema_source_model_schema = SCHEMAS_NS.schema_model('SchemaSource', {
#})


VALIDATE_NS = Namespace('validate','Validation results namespace')

wcv = fields.Wildcard(fields.Raw)
validation_input_model = VALIDATE_NS.model('ValidationInput', {
	'*': wcv
})

validation_model = VALIDATE_NS.model('Validation', {
	'file': fields.String(required=True, description = 'The filename of the JSON which was validated, if it was available'),
	'validated': fields.Boolean(required=True, description = "Validation result"),
	'errors': fields.List(fields.Nested(schema_error_model),required=False, description = 'The list of detected errors when the JSON is processed'),
})

#file_upload = reqparse.RequestParser()
file_upload = VALIDATE_NS.parser()
file_upload.add_argument('file',
	location='files',
	type=werkzeug.datastructures.FileStorage,
	# This line can be uncommented to support multiple uploads when
	# Swagger-UI fixes this case
	#action='append',
	required=True,	
	help='JSON to be validated'
)