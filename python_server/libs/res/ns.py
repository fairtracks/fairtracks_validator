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

ROUTES={
	'ns': NS,
	'path': '/',
	# Nothing done (yet!)
	'routes': [
		(FTVInfo,'info')
	]
}