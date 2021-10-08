#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

from .ftv_models import FTVResource, NS, ftv_info_model

# Now, the routes
class FTVInfo(FTVResource):
	'''Shows FAIRtracks validator info, like API version'''
	@NS.doc('ftv_info')
	@NS.marshal_with(ftv_info_model)
	def get(self):
		'''List all schemas'''
		return self.ftv.ftv_info()

shutParser = NS.parser()
shutParser.add_argument('shutdown_key', type=str, location='json', required=True, help='The shutdown key')

@NS.param('shutdown_key', 'The shutdown key', _in='body')
class FTVShutdown(FTVResource):
	'''It shuts down the server instances, forcing them to reload'''
	@NS.response(201, 'Shutdown in progress')
	@NS.response(403, 'Wrong shutdown key')
	@NS.doc('ftv_shutdown')
	def post(self):
		'''It shuts down the server instances, useful for debugging purposes'''
		pArgs = shutParser.parse_args()
		http_code = 201  if self.ftv.request_shutdown(pArgs.get('shutdown_key')) else 403
		return [], http_code

ROUTES={
	'ns': NS,
	'path': '/',
	# Nothing done (yet!)
	'routes': [
		(FTVInfo, 'info'),
		(FTVShutdown, 'shutdown'),
	]
}