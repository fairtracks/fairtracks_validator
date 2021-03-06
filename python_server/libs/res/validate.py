#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import sys, os

from .ftv_models import FTVResource, VALIDATE_NS, validation_input_model, validation_model, file_upload

from flask import request
#from flask_accept import accept

# These are needed to handle incoming archives
import zipfile
import tarfile
import gzip
import io
import tempfile
import shutil
import json

# And this is needed to guess a bit
import filetype

# Now, the routes

class Validation(FTVResource):
	'''Validates a JSON against the recorded JSON Schemas'''
	@VALIDATE_NS.doc('validate')
	@VALIDATE_NS.expect(validation_input_model)
	@VALIDATE_NS.marshal_with(validation_model, code=200, description='Success', skip_none=True)
	#@VALIDATE_NS.doc(body=validation_input_model)
	@VALIDATE_NS.response(400, 'Input is not JSON content')
#	@accept('application/json')
	def post(self):
		'''It validates the input JSON against the recorded JSON schemas'''
		retval = {}
		http_code = 400
		retval_headers = {}
		
		json_data = request.get_json(silent=True)
		if json_data is not None:
			# It means the input is JSON (as expected), but nothing more
			http_code = 200
			
			retval_tuple = self.ftv.validate(json_data)[0]
			if isinstance(retval_tuple,tuple):
				retval = retval_tuple[0]
				http_code = retval_tuple[1]
				if len(retval_tuple) >= 3:
					retval_headers = retval_tuple[2]
			else:
				retval = retval_tuple
		else:
			retval = {'validated': False, 'errors': [{'reason': 'fatal', 'description': 'There were problems processing incoming JSON (is it a valid one?)'}]}
		
		return retval, http_code, retval_headers

class ArrayValidation(FTVResource):
	'''Validates a JSON against the recorded JSON Schemas'''
	@VALIDATE_NS.doc('validate_array')
	@VALIDATE_NS.expect([validation_input_model])
	@VALIDATE_NS.marshal_list_with(validation_model, code=200, description='Success', skip_none=True)
	@VALIDATE_NS.response(400, 'Input is not a JSON array content')
#	@accept('application/json')
	def post(self):
		'''It validates the input array of JSONs against the recorded JSON schemas'''
		retval = []
		http_code = 400
		retval_headers = {}
		
		json_data = request.get_json(silent=True)
		if isinstance(json_data,list):
			# It means the input is a JSON array (as expected), but nothing more
			http_code = 200
			retval_tuple = self.ftv.validate(*json_data)
			
			if isinstance(retval_tuple,tuple):
				retval = retval_tuple[0]
				http_code = retval_tuple[1]
				if len(retval_tuple) >= 3:
					retval_headers = retval_tuple[2]
			else:
				retval = retval_tuple
		else:
			retval.append({'validated': False, 'errors': [{'reason': 'fatal', 'description': 'There were problems processing incoming JSON array (is it a valid one?)'}]})
		
		return retval , http_code , retval_headers

class ArchiveValidation(FTVResource):
	'''Validates a JSON against the recorded JSON Schemas'''
	@VALIDATE_NS.doc('validate_archive')
	@VALIDATE_NS.marshal_list_with(validation_model, code=200, description='Success', skip_none=True)
	@VALIDATE_NS.response(400, 'The input was not a supported, valid archive')
#	@accept('application/zip','application/x-tar','application/x-gtar','application/x-gtar-compressed')
	def post(self):
		'''It validates the input archive full of JSONs the recorded JSON schemas'''
		retval = []
		http_code = 400
		retval_headers = {}
		workdir = None
		
		raw_data = request.get_data()
		mime_type = filetype.guess_mime(raw_data)
		
		if mime_type == 'application/zip':
			with zipfile.ZipFile(io.BytesIO(raw_data)) as inzip:
				# We need a temporary directory
				workdir = tempfile.mkdtemp(prefix="ftv", suffix="upz")
				try:
					# The internal library knows how to deal with directories
					inzip.extractall(path=workdir)
				except:
					# Something wrong happened
					shutil.rmtree(workdir,ignore_errors=True)
					workdir = None
					retval.append({'validated': False, 'errors': [{'reason': 'fatal', 'description': 'There were problems processing incoming zip archive (is it a valid one?)'}]})
		
		elif mime_type in ('application/x-tar','application/x-gtar','application/x-gtar-compressed','application/gzip','application/x-bzip2'):
			with tarfile.open(fileobj=io.BytesIO(raw_data)) as intar:
				# We need a temporary directory
				workdir = tempfile.mkdtemp(prefix="ftv", suffix="upt")
				# Beware this operation can be unsafe, as
				# tarfile library is unsafe. i.e. a tar
				# could be used as a Trojan horse to
				# hijack the server
				try:
					# The internal library knows how to deal with directories
					intar.extractall(path=workdir)
				except:
					# Something wrong happened
					shutil.rmtree(workdir,ignore_errors=True)
					workdir = None
					retval.append({'validated': False, 'errors': [{'reason': 'fatal', 'description': 'There were problems processing incoming tar archive (is it a valid one?)'}]})
		else:
			retval.append({'validated': False, 'errors': [{'reason': 'fatal', 'description': 'Unsupported or mis-identified input archive (mime {}, size {})'.format(mime_type,len(raw_data))}]})
			
			
		if workdir is not None:
			retval_tuple = self.ftv.validate((workdir,None))
			
			if isinstance(retval_tuple,tuple):
				retval = retval_tuple[0]
				http_code = retval_tuple[1]
				if len(retval_tuple) >= 3:
					retval_headers = retval_tuple[2]
			else:
				retval = retval_tuple
			
			# Temporary directory and its contents
			# are not needed any more
			shutil.rmtree(workdir,ignore_errors=True)
			
			if http_code < 500:
				# If some element had failures, then the
				# returned code is still 200
				http_code = 200
				for ele in retval:
					# As parsed objects could have absolute paths,
					# We have to trim them
					ele['file'] = os.path.relpath(ele['file'],workdir)
		
		return retval , http_code , retval_headers

class MultipartValidation(FTVResource):
	'''Validates a JSON against the recorded JSON Schemas'''
	@VALIDATE_NS.doc('validate_multipart')
	@VALIDATE_NS.marshal_list_with(validation_model, code=200, description='Success', skip_none=True)
	@VALIDATE_NS.response(400, 'Some of the validations failed')
	@VALIDATE_NS.expect(file_upload)
	#@VALIDATE_NS.produces(['image/png'])
#	@accept('multipart/form-data')
	def post(self):
		'''It validates the input JSON files against the recorded JSON schemas'''
		retval = []
		failed_retval = []
		retval_headers = {}
		http_code = 400
		
		json_data = []
		workdir_data = []
		if request.files is not None:
			for formfiles in request.files.listvalues():
				for formfile in formfiles:
					client_file = formfile.filename
					file_content = formfile.read()
					mime_type = filetype.guess_mime(file_content)
					
					if mime_type == 'application/zip':
						with zipfile.ZipFile(io.BytesIO(file_content)) as inzip:
							# We need a temporary directory
							workdir = tempfile.mkdtemp(prefix="ftv", suffix="upz")
							try:
								# The internal library knows how to deal with directories
								inzip.extractall(path=workdir)
								workdir_data.append((client_file,workdir))
								json_data.append((workdir,None))
							except:
								# Something wrong happened
								shutil.rmtree(workdir,ignore_errors=True)
								workdir = None
								retval.append({'file': client_file,'validated': False, 'errors': [{'reason': 'fatal', 'description': 'There were problems processing incoming zip archive (is it a valid one?)'}]})
					elif mime_type in ('application/x-tar','application/x-gtar','application/x-gtar-compressed','application/gzip','application/x-bzip2'):
						with tarfile.open(fileobj=io.BytesIO(file_content)) as intar:
							# We need a temporary directory
							workdir = tempfile.mkdtemp(prefix="ftv", suffix="upt")
							# Beware this operation can be unsafe, as
							# tarfile library is unsafe. i.e. a tar
							# could be used as a Trojan horse to
							# hijack the server
							try:
								# The internal library knows how to deal with directories
								intar.extractall(path=workdir)
								workdir_data.append((client_file,workdir))
								json_data.append((workdir,None))
							except:
								# Something wrong happened
								shutil.rmtree(workdir,ignore_errors=True)
								workdir = None
								retval.append({'file': client_file,'validated': False, 'errors': [{'reason': 'fatal', 'description': 'There were problems processing incoming tar archive (is it a valid one?)'}]})
					elif (mime_type == 'application/json')  or ((mime_type is None) and (formfile.mimetype in ('application/json','application/octet-stream'))) :
						try:
							jsonStr = file_content.decode("utf-8")
							jsonDoc = json.loads(jsonStr)
							json_data.append((client_file,jsonDoc))
						except BaseException as e:
							# Recording the error
							failed_retval.append({'file': client_file, 'validated': False, 'errors':[{'reason': 'fatal', 'description': 'Unable to open/parse JSON file'}]})
					else:
						failed_retval.append({'file': client_file, 'validated': False, 'errors':[{'reason': 'fatal', 'description': 'Unable to open/parse file: unrecognized format'}]})
		else:
			failed_retval.append({'validated': False, 'errors': [{'reason': 'fatal', 'description': 'There were problems processing incoming files from form'}]})
		
		if json_data:
			retval_tuple = self.ftv.validate(*json_data)
			
			if isinstance(retval_tuple,tuple):
				retval = retval_tuple[0]
				http_code = retval_tuple[1]
				if len(retval_tuple) >= 3:
					retval_headers = retval_tuple[2]
			else:
				retval = retval_tuple
			
			# Cleaning up resources
			for _,workdir in workdir_data:
				shutil.rmtree(workdir,ignore_errors=True)
			
			if http_code < 500:
				for ele in retval:
					# As parsed objects could have absolute paths,
					# We have to trim them
					for client_archive, workdir in workdir_data:
						if ele['file'].startswith(workdir):
							client_path = os.path.relpath(ele['file'],workdir)
							
							ele['file'] = client_archive + '::' + client_path
							break
				
				# If some element had failures, then the
				# returned code is still 200
				http_code = 200
				if len(failed_retval) > 0:
					retval.extend(failed_retval)
		else:
			retval = failed_retval
		
		return retval , http_code

ROUTES={
	'ns': VALIDATE_NS,
	'path': '/validate',
	'routes': [
		(Validation,''),
		(ArrayValidation,'/array'),
		(ArchiveValidation,'/archive'),
		(MultipartValidation,'/multipart'),
	]
}
