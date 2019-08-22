#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

from .ftv_models import FTVResource, SCHEMAS_NS, schema_info_model, schema_source_model

# Now, the routes
class SchemasList(FTVResource):
	'''Shows a list of all the setup schemas'''
	@SCHEMAS_NS.doc('list_schemas')
	@SCHEMAS_NS.marshal_list_with(schema_info_model,skip_none=True)
	def get(self):
		'''List all schemas'''
		return self.ftv.list_schemas()

@SCHEMAS_NS.response(404, 'Schema not found')
@SCHEMAS_NS.param('schema_hash', 'The schema hash')
class SchemaInfo(FTVResource):
	'''Return the detailed information of a gene'''
	@SCHEMAS_NS.doc('schema')
	@SCHEMAS_NS.marshal_with(schema_info_model,skip_none=True)
	def get(self,schema_hash):
		'''It gets detailed schema processing information'''
		return self.ftv.get_schema_info(schema_hash)

@SCHEMAS_NS.response(404, 'Schema not found')
@SCHEMAS_NS.param('schema_hash', 'The schema hash')
class Schema(FTVResource):
	'''Return the detailed information of a gene'''
	@SCHEMAS_NS.doc('schema_source')
	@SCHEMAS_NS.marshal_with(schema_source_model)
	def get(self,schema_hash):
		'''It gets the cached schema (if available)'''
		return self.ftv.get_schema(schema_hash)

ROUTES={
	'ns': SCHEMAS_NS,
	'path': '/schemas',
	'routes': [
		(SchemasList,''),
		(SchemaInfo,'/<string:schema_hash>'),
		(Schema,'/<string:schema_hash>/schema')
	]
}
