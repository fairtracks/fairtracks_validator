#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding: utf-8

import os, sys
import tempfile
import re
import json
import datetime

from urllib import request
from urllib.error import *
import http,socket
import time

import collections

import atexit
import shutil

from fairtracks_validator.validator import FairGTracksValidator

from .rw_file_lock import RWFileLock , LockError

class FAIRTracksValidatorSingleton(object):
	APIVersion = "0.3.1"
	HexSHAPattern = re.compile('^[0-9a-f]{2,}$')
	CacheManifestFile = 'manifest.json'
	
	DEFAULT_MAX_RETRIES = 5
	DEFAULT_INVALIDATION_KEY = "InvalidateCachePleasePleasePlease!!!"
	
	def __init__(self,local_config,api=None):
		self.api = api
		self._debug = False
		self.max_retries = self.DEFAULT_MAX_RETRIES
		
		# This variable should be honoured by the API
		# so no query is allowed meanwhile we are offline
		self.offline = True
		
		# Let's initialize the whole system
		self.config = local_config
		self.cacheDir = self.config.get('cacheDir')
		
		if self.cacheDir is None:
			self.cacheDir = tempfile.mkdtemp(prefix="ftv", suffix="cache")
			# Remember to remove the directory at exit
			atexit.register(shutil.rmtree, self.cacheDir, ignore_errors=True)
			self.config['cacheDir'] = self.cacheDir
		
		self.schemaCacheDir = os.path.join(self.cacheDir,'schema_cache')
		
		if not os.path.isdir(self.schemaCacheDir):
			os.makedirs(self.schemaCacheDir)
		
		schemaCacheLockFile = os.path.join(self.cacheDir,'schema_cache.lock')
		extensionsCacheLockFile = os.path.join(self.cacheDir,'extensions_cache.lock')
		
		self.SchemaCacheLock = RWFileLock(filename=schemaCacheLockFile)
		
		self.ExtensionsCacheLock = RWFileLock(filename=extensionsCacheLockFile)
		
		self.invalidation_key = local_config.get('invalidation_key',self.DEFAULT_INVALIDATION_KEY)
		
		self.init_server()
	
	def init_server(self):
		self.offline = True
		with self.SchemaCacheLock.exclusive_blocking_lock():
			self._init_server()
		
		with self.ExtensionsCacheLock.exclusive_blocking_lock():
			self.fgv.warmUpCaches()
		
		self.offline = False
	
	def _init_server(self):
		# The server is initialized
		self.fgv = FairGTracksValidator(config=self.config)
		
		# Do this in a separate thread
		self.init_cache()
		self.validateCachedJSONSchemas()
	
	def init_cache(self):
		# 1. Cache directory should exist at this point
		# These variables are dictionaries to check whether we are reading something twice
		schemas = []
		
		# 2. Read previous cache manifest
		manifest_path = os.path.join(self.schemaCacheDir,self.CacheManifestFile)
		manifest = {}
		if os.path.isfile(manifest_path):
			try:
				with open(manifest_path,'r',encoding='utf-8') as mh:
					manifest = json.load(mh,object_pairs_hook=collections.OrderedDict)
			except OSError as err:
				# The manifest is unreadable, skip it
				pass
			except json.JSONDecodeError as jde:
				# The manifest is either empty or corrupted, skip it
				pass
			else:
				# 2.a. Process previous cache state
				for schema in manifest.get('schemas',[]):
					# TODO: cache invalidation routines
					schema_hash = schema.get('schema_hash')
					source_urls = schema.get('source_urls',[])
					if (schema_hash is not None) and len(source_urls) > 0:
						schemas.append(schema)
		
		# Setting the timestamp of the manifest generation
		manifest['updated'] = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
		self.manifest = manifest
		
		# 3. Pre-populating the list
		initial_source_urls = self.config.get('schemas',[])
		self.initial_source_urls = initial_source_urls
		if len(initial_source_urls) > 0:
			schemas.append({'source_urls': initial_source_urls})
		
		# 4. Initialize empty curated list of JSON Schemas
		curated_schemas_by_hash = {}
		curated_schemas_by_url = {}
		curated_schemas = []
		
		# 5. Curation loop
		for schema_info in schemas:
			# Skipping defective entries
			if 'source_urls' not in schema_info:
				continue
			
			source_urls = schema_info['source_urls']
			
			# 5.a. Does it already have its JSON Schema hash?
			schema_hash = schema_info.get('schema_hash')
			
			# Files which do not seem a hash are skipped
			curated_schema = None
			if (schema_hash is not None) and self.HexSHAPattern.search(schema_hash):
				curated_schema = curated_schemas_by_hash.get(schema_hash)
				# The schema has not been curated yet
				if curated_schema is None:
					jsc_path = schema_hash
					full_jsc_path = os.path.join(self.schemaCacheDir,jsc_path)
					
					if os.path.isfile(full_jsc_path):
						# If it is a file, let's parse it
						try:
							with open(full_jsc_path,'r',encoding='utf-8') as jssh:
								jss = json.load(jssh,object_pairs_hook=collections.OrderedDict)
						except OSError as err:
							# The JSON Schema is unreadable, invalidate it
							schema_hash = None
						except json.JSONDecodeError as jde:
							# The JSON Schema is either empty or corrupted, invalidate it
							schema_hash = None
						else:
							# The double-check of the cache
							computed_schema_hash = FairGTracksValidator.GetNormalizedJSONHash(jss)
							if schema_hash == computed_schema_hash:
								curated_schema_info = {
									'fetched_at': schema_info.get('fetched_at'),
									'schema_hash': schema_hash,
									'source_urls': source_urls
								}
								curated_schema = {
									'info': curated_schema_info,
									'source': jss
								}
								errors = schema_info.get('errors',[])
								schema_id = schema_info.get('schema_id')
								
								if schema_id is not None:
									curated_schema_info['schema_id'] = schema_id
								#elif len(errors) == 0:
								#	errors.append({
								#		'reason': 'no_schema_id',
								#		'description': "The JSON does not have either an 'id' or '$id'"
								#	})
								
								if len(errors) > 0:
									curated_schema_info['errors'] = errors
							else:
								# Hashes do not match, invalidate it
								schema_hash = None
			
			# We are here when it is either invalidated or fresh
			curated_schemas_to_populate = []
			if curated_schema is None:
				for source_url in source_urls:
					# Time to try fetching it
					errors = []
					schema_hash = None
					schema_id = None
					jss = None
					theRequest = request.Request(source_url)
					try:
						theRawData = self.retriable_full_http_read(theRequest)
					except HTTPError as e:
						errors.append({
							'reason': 'network',
							'description': str(e)
						})
					except socket.timeout as e:
						errors.append({
							'reason': 'network',
							'description': str(e)
						})
					except Exception as e:
						errors.append({
							'reason': 'unexpected',
							'description': str(e)
						})
					else:
						try:
							jss = json.loads(theRawData.decode('utf-8'),object_pairs_hook=collections.OrderedDict)
						except UnicodeError as ue:
							errors.append({
								'reason': 'decode',
								'description': str(ue)
							})
						except json.JSONDecodeError as jde:
							# The JSON Schema is either empty or corrupted, invalidate it
							errors.append({
								'reason': 'json',
								'description': str(jde)
							})
						except Exception as e:
							errors.append({
								'reason': 'unexpected',
								'description': str(e)
							})
						else:
							schema_hash = FairGTracksValidator.GetNormalizedJSONHash(jss)
							
							# Is this an schema?
							#if jss.get('$schema') is not None:
							#	id_key = '$id'  if '$id' in jss else 'id'
							#	schema_id = jss.get(id_key)
							#	if schema_id is None:
							#		errors.append({
							#			'reason': 'no_id',
							#			'description': "JSON Schema attribute '$id' or 'id' are missing"
							#		})
							#else:
							#	errors.append({
							#		'reason': 'no_schema',
							#		'description': "JSON Schema attribute '$schema' is missing"
							#	})
							
							# Only here it is saved to the caching dir
							jsc_path = schema_hash
							full_jsc_path = os.path.join(self.schemaCacheDir,jsc_path)
							try:
								# Save it!
								with open(full_jsc_path,'wb') as jssh:
									jssh.write(theRawData)
							except OSError as err:
								errors.append({
									'reason': 'cache_save',
									'description': str(err)
								})
								# The JSON Schema is unreadable, invalidate it
								schema_hash = None
					
					curated_schema_info = {
						'fetched_at': datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat(),
						'source_urls': [ source_url ]
					}
					
					curated_schema = {
						'info': curated_schema_info
					}
					
					if jss is not None:
						curated_schema['source'] = jss
					
					if schema_hash is not None:
						curated_schema_info['schema_hash'] = schema_hash
					
					if schema_id is not None:
						curated_schema_info['schema_id'] = schema_id
					
					if len(errors) > 0:
						curated_schema_info['errors'] = errors
					
					# Store it for the last step
					curated_schemas_to_populate.append(curated_schema)
			else:
				curated_schemas_to_populate.append(curated_schema)
			
			# 5.b. Register each schema (if possible)
			for curated_schema in curated_schemas_to_populate:
				curated_schema_info = curated_schema['info']
				schema_hash = curated_schema_info.get('schema_hash')
				source_urls = curated_schema_info.get('source_urls')
				
				candidate_to_store = False
				prev_curated_schema = None
				if schema_hash is not None:
					prev_curated_schema = curated_schemas_by_hash.get(schema_hash)
					candidate_to_store = prev_curated_schema is None
				
				curated_source_urls = []
				target_curated_schema = curated_schema  if prev_curated_schema is None else prev_curated_schema
				for source_url in source_urls:
					if source_url not in curated_schemas_by_url:
						curated_source_urls.append(source_url)
						curated_schemas_by_url[source_url] = target_curated_schema
					
				if len(curated_source_urls) > 0:
					if candidate_to_store:
						# Store the JSON Schema source
						curated_schema_info['source_urls'] = curated_source_urls
						
						# Now, record the curated schema
						curated_schemas_by_hash[schema_hash] = curated_schema
						curated_schemas.append(curated_schema)
					else:
						# We only update the list of source_urls
						prev_curated_schema['info'].setdefault('source_urls',[]).extend(curated_source_urls)
		
		# Saving the populated hashes
		self._schemas = curated_schemas_by_hash
		
		# 6. Save the updated manifest
		self.manifest['schemas'] = list(filter(lambda si: si is not None, map(lambda cs: cs.get('info'), curated_schemas)))
		
		with open(manifest_path,'w',encoding='utf-8') as mh:
			json.dump(self.manifest, mh)
	
	def validateCachedJSONSchemas(self):
		cached_schemas = map(lambda curated_schema: {'schema': curated_schema['source'], 'file': curated_schema['info']['source_urls'][0], 'errors': curated_schema['info'].setdefault('errors',[])}, self._schemas.values())
		self.fgv.loadJSONSchemas(*cached_schemas)
		
	
	# This method is borrowed from
	# https://github.com/inab/opeb-enrichers/blob/533b6f6aa93acc7f1f950bf4a37ee4d740a2965a/pubEnricher/libs/skeleton_pub_enricher.py#L603
	# This method does the different reads and retries
	# in case of partial contents
	def retriable_full_http_read(self,theRequest,timeout=300,debug_url=None):
		retries = 0
		
		last_exception = None
		while retries <= self.max_retries:
			try:
				# The original bytes
				response = b''
				with request.urlopen(theRequest,timeout=timeout) as req:
					while True:
						try:
							# Try getting it
							responsePart = req.read()
						except http.client.IncompleteRead as icread:
							# Getting at least the partial content
							response += icread.partial
							continue
						else:
							# In this case, saving all
							response += responsePart
						break
				
				return response
			except HTTPError as e:
				if e.code >= 500 and retries < self.max_retries:
					# Using a backoff time of 2 seconds when 500 or 502 errors are hit
					retries += 1
					
					if self._debug:
						print("Retry {0} , due code {1}".format(retries,e.code),file=sys.stderr)
					
					time.sleep(2**retries)
					last_exception = e
				else:
					if debug_url is not None:
						print("URL with ERROR: "+debug_url+"\n",file=sys.stderr)
						sys.stderr.flush()
					raise e
			except socket.timeout as e:
				# Using also a backoff time of 2 seconds when read timeouts occur
				retries += 1
				
				if self._debug:
					print("Retry {0} , due timeout".format(retries),file=sys.stderr)
				
				time.sleep(2**retries)
				last_exception = e
		
		# If we reach this point, there is an exception in betweenm
		raise last_exception
	
	def set_api_instance(self,api):
		self.api = api
	
	# Next methods are called from the different endpoint implementations
	# (indeed, they are the endpoint implementations!)
	
	def invalidate_cache(self,invalidation_key,invalidateExtensionsCache=False):
		# Cleaning up the cached schemas
		if self.invalidation_key == invalidation_key:
			self.offline = True
			
			# Removing only the schemas cache
			with self.SchemaCacheLock.exclusive_blocking_lock():
				for elem in os.scandir(path=self.schemaCacheDir):
					if elem.is_dir() and not elem.is_symlink():
						shutil.rmtree(elem.path, ignore_errors=True)
					else:
						os.remove(elem.path)
			
			# Also removing the extensions cache
			if invalidateExtensionsCache:
				with self.ExtensionsCacheLock.exclusive_blocking_lock():
					self.ftv.invalidateCaches()
			
			self.init_server()
			
			return True
		else:
			return False
	
	BEING_UPDATED_RESPONSE=(['Server temporarily'], 503, {'Retry-After': '60'})
	
	def ftv_info(self):
		try:
			with self.SchemaCacheLock.shared_lock():
				return { 'version': self.APIVersion, 'config': {'schemas': self.initial_source_urls } }
		except LockError:
			return self.BEING_UPDATED_RESPONSE
		
	
	def list_schemas(self):
		try:
			with self.SchemaCacheLock.shared_lock():
				return self.manifest['schemas']
		except LockError:
			return self.BEING_UPDATED_RESPONSE
	
	def get_schema_info(self,schema_hash):
		try:
			with self.SchemaCacheLock.shared_lock():
				_schema = self._schemas.get(schema_hash)
				if _schema is None:
					self.api.abort(404, 'JSON Schema whose hash is {} is not recorded'.format(schema_hash))
				
				return _schema['info']
		except LockError:
			return self.BEING_UPDATED_RESPONSE
	
	def get_schema(self,schema_hash):
		try:
			with self.SchemaCacheLock.shared_lock():
				_schema = self._schemas.get(schema_hash)
				_schema_source = None  if _schema is None else _schema.get('source')
				if _schema_source is None:
					self.api.abort(404, 'JSON Schema source whose hash is {} is not recorded'.format(schema_hash))
				
				return _schema_source
		except LockError:
			return self.BEING_UPDATED_RESPONSE
	
	def validate(self,*json_data):
		try:
			with self.SchemaCacheLock.shared_lock(), self.ExtensionsCacheLock.shared_lock():
				cached_jsons = []
				for i_json, loaded_json_piece in enumerate(json_data):
					if isinstance(loaded_json_piece,tuple):
						loaded_json_path , loaded_json = loaded_json_piece
					else:
						loaded_json_path = '(inline'+str(i_json)+')'
						loaded_json = loaded_json_piece
					
					if loaded_json is None:
						cached_jsons.append(loaded_json_path)
					else:
						cached_jsons.append({'json': loaded_json, 'file': loaded_json_path, 'errors': []})
				
				# As the input may be a directory full of JSONs, the output
				# from this method is the only authorizative source of what
				# happened inside the validation
				parsed_jsons = self.fgv.jsonValidate(*cached_jsons)
				
				return list(map(lambda jsonObj: {
					'file': jsonObj['file'],
					'validated': len(jsonObj['errors'])==0,
					'errors': jsonObj['errors'],
					'schema_id': jsonObj.get('schema_id'),
					'schema_hash': jsonObj.get('schema_hash')
				}, parsed_jsons))
		except LockError:
			return self.BEING_UPDATED_RESPONSE
	
		
