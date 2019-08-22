#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

from flask_restplus import Namespace, Api, Resource, fields

class FTVResource(Resource):
	'''This class eases passing the instance of the validator API'''
	def __init__(self,api=None,*args,**kwargs):
		super().__init__(api,*args,**kwargs)
		self.ftv = kwargs['ftv']



NS = Namespace('ftv','FAIRtracks REST validator')

ftv_info_model = NS.model('FTVInfo', {
	'version': fields.String(required=True, description = 'API Version'),
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
	'validated': fields.Boolean(required=True, description = "Validation result"),
	'errors': fields.List(fields.Nested(schema_error_model),required=False, description = 'The list of detected errors when the JSON is processed'),
})
