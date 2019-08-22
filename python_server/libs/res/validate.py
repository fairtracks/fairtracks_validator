#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

from .ftv_models import FTVResource, VALIDATE_NS, validation_input_model, validation_model

from flask import request

# Now, the routes

@VALIDATE_NS.response(400, 'Validation failed')
class Validation(FTVResource):
	'''Validates a JSON against the recorded JSON Schemas'''
	@VALIDATE_NS.doc('validate')
	@VALIDATE_NS.expect(validation_input_model)
	@VALIDATE_NS.marshal_with(validation_model,skip_none=True)
	def post(self):
		'''It validates the input JSON Schema'''
		json_data = request.get_json()
		return self.ftv.validate(json_data)[0]

ROUTES={
	'ns': VALIDATE_NS,
	'path': '/validate',
	'routes': [
		(Validation,'')
	]
}
