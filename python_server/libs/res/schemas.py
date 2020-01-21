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

class AbstractSchemasInvalidate(FTVResource):
	'''It invalidates the cached schemas'''
	def invalidate(self,invalidation_key,invalidateExtensionsCache):
		'''It invalidates the cached JSON schemas, forcing to fetch them again'''
		http_code = 200  if self.ftv.invalidate_cache(invalidation_key,invalidateExtensionsCache) else 403
		return [], http_code

class SchemasInvalidate(AbstractSchemasInvalidate):
	'''It invalidates the cached schemas'''
	@SCHEMAS_NS.response(200, 'Cached JSON Schemas have been fetched again')
	@SCHEMAS_NS.response(403, 'Wrong invalidation key')
	@SCHEMAS_NS.doc('schemas_invalidate')
	def delete(self,invalidation_key):
		'''It invalidates the cached JSON schemas, forcing to fetch them again'''
		return self.invalidate(invalidation_key,False)
	
class SchemasFullInvalidate(AbstractSchemasInvalidate):
	'''It fully invalidates the cached schemas'''
	@SCHEMAS_NS.response(200, 'Cached JSON Schemas have been fetched again')
	@SCHEMAS_NS.response(403, 'Wrong invalidation key')
	@SCHEMAS_NS.doc('schemas_invalidate')
	def delete(self,invalidation_key):
		'''It invalidates the cached JSON schemas, forcing to fetch them again'''
		return self.invalidate(invalidation_key,True)

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
		(SchemasInvalidate,'/invalidate/<string:invalidation_key>'),
		(SchemasFullInvalidate,'/invalidate/<string:invalidation_key>/full'),
		(SchemaInfo,'/<string:schema_hash>'),
		(Schema,'/<string:schema_hash>/schema')
	]
}
