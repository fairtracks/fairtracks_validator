#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import os
import re
import json
import jsonschema as JSV
import uritools
import hashlib

from collections import namedtuple

# This is needed to assure open suports encoding parameter
if sys.version_info[0] > 2:
	ALLOWED_KEY_TYPES=(bytes,str)
	ALLOWED_ATOMIC_VALUE_TYPES=(int,bytes,str,float,bool)
	# py3k
	pass
else:
	ALLOWED_KEY_TYPES=(str,unicode)
	ALLOWED_ATOMIC_VALUE_TYPES=(int,long,str,unicode,float,bool)
	# py2
	import codecs
	import warnings
	def open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
		if newline is not None:
			warnings.warn('newline is not supported in py2')
		if not closefd:
			warnings.warn('closefd is not supported in py2')
		if opener is not None:
			warnings.warn('opener is not supported in py2')
		return codecs.open(filename=file, mode=mode, encoding=encoding, errors=errors, buffering=buffering)


# Augmenting the supported types
from fairtracks_validator.extensions.curie_search import CurieSearch
from fairtracks_validator.extensions.ontology_term import OntologyTerm
from fairtracks_validator.extensions.unique_check import UniqueKey
from fairtracks_validator.extensions.pk_check import PrimaryKey
from fairtracks_validator.extensions.fk_check import ForeignKey

from .extend_validator import extendValidator , traverseJSONSchema , PLAIN_VALIDATOR_MAPPER

class ExtensibleValidator(object):
	CustomBaseValidators = {
		None: [
			UniqueKey,
			PrimaryKey,
			ForeignKey
		]
	}
	
	SCHEMA_KEY = '$schema'
	ALT_SCHEMA_KEYS = [
		'@schema',
		'_schema',
		SCHEMA_KEY
	]
	
	def __init__(self,customFormats=[], customTypes={}, customValidators=CustomBaseValidators, config={}):
		self.schemaHash = {}
		self.refSchemaCache = {}
		self.refSchemaSet = {}
		self.customFormatCheckerInstance = JSV.FormatChecker()

		# Registering the custom formats, in order to use them
		for customFormat in customFormats:
			self.customFormatCheckerInstance.checks(customFormat.FormatName)(customFormat.IsCorrectFormat)
		
		self.customTypes = customTypes
		self.customValidators = customValidators
		self.config = config
		self.doNotValidateNoId = not bool(config.get('validate-no-id',True))
	
	@classmethod
	def FindFKs(cls,jsonSchema,jsonSchemaURI,prefix=""):
		FKs = []
		
		if isinstance(jsonSchema,dict):
			# First, this level's foreign keys
			isArray = False
			
			if 'items' in jsonSchema and isinstance(jsonSchema['items'],dict):
				jsonSchema = jsonSchema['items']
				isArray = True
				
				if prefix!='':
					prefix += '[]'
			
			if 'foreign_keys' in jsonSchema and isinstance(jsonSchema['foreign_keys'],(list,tuple)):
				for fk_def in jsonSchema['foreign_keys']:
					# Only valid declarations are taken into account
					if isinstance(fk_def,dict) and 'schema_id' in fk_def and 'members' in fk_def:
						ref_schema_id = fk_def['schema_id']
						members = fk_def['members']
						
						if isinstance(members,(list,tuple)):
							# Translating to absolute URI (in case it is relative)
							abs_ref_schema_id = uritools.urijoin(jsonSchemaURI,ref_schema_id)
							
							# Translating the paths
							components = tuple(map(lambda component: prefix + '.' + component  if component not in ['.','']  else prefix, members))
							
							FKs.append((abs_ref_schema_id,components))
			
			# Then, the foreign keys inside sublevels
			if 'properties' in jsonSchema and isinstance(jsonSchema['properties'],dict):
				if prefix != '':
					prefix += '.'
				p = jsonSchema['properties']
				for k,subSchema in p.items():
					FKs.extend(cls.FindFKs(subSchema,jsonSchemaURI,prefix+k))
		
		return FKs
	
	def loadJSONSchemas(self,*args,verbose=None):
		p_schemaHash = self.schemaHash
		# Schema validation stats
		numDirOK = 0
		numDirFail = 0
		numFileOK = 0
		numFileIgnore = 0
		numFileFail = 0
		
		if verbose:
			print("PASS 0.a: JSON schema loading and cache generation")
		jsonSchemaPossibles = list(args)
		jsonSchemaNext = []
		refSchemaCache = self.refSchemaCache = {}
		refSchemaFile = {}
		refSchemaSet = self.refSchemaSet = {}
		inlineCounter = 0
		for jsonSchemaPossible in jsonSchemaPossibles:
			schemaObj = None
			
			if isinstance(jsonSchemaPossible,dict):
				schemaObj = jsonSchemaPossible
				errors = schemaObj.get('errors')
				if errors is None:
					if verbose:
						print("\tIGNORE: cached schema does not have the mandatory 'errors' attribute, so it cannot be processed")
					numFileIgnore += 1
					continue
				
				jsonSchema = schemaObj.get('schema')
				if jsonSchema is None:
					if verbose:
						print("\tIGNORE: cached schema does not have the mandatory 'schema' attribute, so it cannot be processed")
					errors.append({
						'reason': 'unexpected',
						'description': "The cached schema is missing"
					})
					numFileIgnore += 1
					continue
				
				schemaObj['schema_hash'] = self.GetNormalizedJSONHash(jsonSchema)
				
				if 'file' not in schemaObj:
					schemaObj['file'] = '(inline schema {})'.format(inlineCounter)
					inlineCounter += 1
				jsonSchemaFile = schemaObj['file']
			elif os.path.isdir(jsonSchemaPossible):
				jsonSchemaDir = jsonSchemaPossible
				# It's a possible JSON Schema directory, not a JSON Schema file
				try:
					for relJsonSchemaFile in os.listdir(jsonSchemaDir):
						if relJsonSchemaFile[0]=='.':
							continue
						
						newJsonSchemaFile = os.path.join(jsonSchemaDir,relJsonSchemaFile)
						if os.path.isdir(newJsonSchemaFile) or '.json' in relJsonSchemaFile:
							jsonSchemaPossibles.append(newJsonSchemaFile)
					numDirOK += 1
				except IOError as ioe:
					if verbose:
						print("FATAL ERROR: Unable to open JSON schema directory {0}. Reason: {1}\n".format(jsonSchemaDir,ioe.strerror),file=sys.stderr)
					numDirFail += 1
				
				continue
			else:
				jsonSchemaFile = jsonSchemaPossible
				if verbose:
					print("* Loading schema {0}".format(jsonSchemaFile))
				try:
					with open(jsonSchemaFile,mode="r",encoding="utf-8") as sHandle:
						jsonSchema = json.load(sHandle)
				except IOError as ioe:
					if verbose:
						print("FATAL ERROR: Unable to open schema file {0}. Reason: {1}".format(jsonSchemaFile,ioe.strerror),file=sys.stderr)
					numFileFail += 1
					continue
				else:
					errors = []
					schemaObj = {
						'schema': jsonSchema,
						'schema_hash': self.GetNormalizedJSONHash(jsonSchema),
						'file': jsonSchemaFile,
						'errors': errors
					}
			
			schemaValId = jsonSchema.get(self.SCHEMA_KEY)
			if schemaValId is None:
				if verbose:
					print("\tIGNORE: {0} does not have the mandatory '{1}' attribute, so it cannot be validated".format(jsonSchemaFile,self.SCHEMA_KEY))
				errors.append({
					'reason': 'no_schema',
					'description': "JSON Schema attribute '{}' is missing".format(self.SCHEMA_KEY)
				})
				numFileIgnore += 1
				continue
			
			if PLAIN_VALIDATOR_MAPPER.get(schemaValId) is None:
				if verbose:
					print("\tIGNORE/FIXME: The JSON Schema id {0} is not being acknowledged by this validator".format(schemaValId))
				errors.append({
					'reason': 'schema_unknown',
					'description': "'$schema' id {0} is not being acknowledged by this validator".format(schemaValId)
				})
				numFileIgnore += 1
				continue
			
			# Getting the JSON Schema URI, needed by this
			idKey = '$id'  if '$id' in jsonSchema else 'id'
			jsonSchemaURI = jsonSchema.get(idKey)
			if jsonSchemaURI is not None:
				if jsonSchemaURI in refSchemaFile:
					if verbose:
						print("\tERROR: schema in {0} and schema in {1} have the same id".format(jsonSchemaFile,refSchemaFile[jsonSchemaURI]),file=sys.stderr)
					errors.append({
						'reason': 'dup_id',
						'description': "schema in {0} and schema in {1} have the same id".format(jsonSchemaFile,refSchemaFile[jsonSchemaURI])
					})
					numFileFail += 1
					continue
				else:
					refSchemaCache[jsonSchemaURI] = jsonSchema
					refSchemaFile[jsonSchemaURI] = jsonSchemaFile
			else:
				numFileIgnore += 1
				if verbose:
					print("\tIGNORE: Schema in {0} has no id attribute".format(jsonSchemaFile),file=sys.stderr)
				if self.doNotValidateNoId:
					errors.append({
						'reason': 'no_id',
						'description': "JSON Schema attributes '$id' (Draft06 onward) and 'id' (Draft04) are missing in {}".format(jsonSchemaFile)
					})
					numFileIgnore += 1
					continue
			
			# We need to store these before creating the validators
			# in order to build the RefSchema cache
			jsonSchemaNext.append(schemaObj)
		
		
		if verbose:
			print("PASS 0.b: JSON schema validation")
		for schemaObj in jsonSchemaNext:
			jsonSchema = schemaObj['schema']
			jsonSchemaFile = schemaObj['file']
			errors = schemaObj['errors']
			
			# Errors related to these are captured in the previous loop
			schemaValId = jsonSchema.get(self.SCHEMA_KEY)
			plain_validator = PLAIN_VALIDATOR_MAPPER.get(schemaValId)
			
			# Getting the JSON Schema URI, needed by this
			idKey = '$id'  if '$id' in jsonSchema else 'id'
			jsonSchemaURI = jsonSchema.get(idKey)
			
			validator , customFormatInstances = extendValidator(jsonSchemaURI, plain_validator, self.customTypes, self.customValidators, config=self.config, jsonSchemaSource=jsonSchemaFile)
			
			schemaObj['customFormatInstances'] = customFormatInstances
			schemaObj['validator'] = validator
			
			# Validate the extended JSON schema properly
			metaSchema = validator.META_SCHEMA
			if len(customFormatInstances) > 0:
				metaSchema = metaSchema.copy()
				metaSchema['properties'] = metaProps = metaSchema['properties'].copy()
				
				for customFormatInstance in customFormatInstances:
					for kF, vF in customFormatInstance.triggerJSONSchemaDef.items():
						if kF in metaProps:
							# Multiple declarations
							vM = metaProps[kF].copy()
							if 'anyOf' not in vM:
								newDecl = {
									'anyOf': [
										vM
									]
								}
								vM = metaProps[kF] = newDecl
							else:
								metaProps[kF] = vM
							
							vM['anyOf'].append(vF)
						else:
							metaProps[kF] = vF
			
			# We need to shadow the original schema
			localRefSchemaCache = refSchemaCache.copy()
			localRefSchemaCache[jsonSchemaURI] = metaSchema
			cachedSchemasResolver = JSV.RefResolver(base_uri=jsonSchemaURI, referrer=metaSchema, store=localRefSchemaCache)
			
			valErrors = [ valError  for valError in validator(metaSchema,resolver = cachedSchemasResolver).iter_errors(jsonSchema) ]
			if len(valErrors) > 0:
				if verbose:
					print("\t- ERRORS:\n"+"\n".join(map(lambda se: "\t\tPath: {0} . Message: {1}".format("/"+"/".join(map(lambda e: str(e),se.path)),se.message) , valErrors))+"\n")
				for valError in valErrors:
					errors.append({
						'reason': 'schema_error',
						'description': "Path: {0} . Message: {1}".format("/"+"/".join(map(lambda e: str(e),valError.path)),valError.message)
					})
				numFileFail += 1
			elif jsonSchemaURI is not None:
				# Getting the JSON Pointer object instance of the augmented schema
				# my $jsonSchemaP = $v->schema($jsonSchema)->schema;
				# This step is done, so we fetch a complete schema
				# $jsonSchema = $jsonSchemaP->data;
				
				if jsonSchemaURI in p_schemaHash:
					if verbose:
						print("\tERROR: validated, but schema in {0} and schema in {1} have the same id".format(jsonSchemaFile,p_schemaHash[jsonSchemaURI]['file']),file=sys.stderr)
					errors.append({
						'reason': 'dup_id',
						'description': "JSON Schema validated, but schema in {0} and schema in {1} have the same id".format(jsonSchemaFile,p_schemaHash[jsonSchemaURI]['file'])
					})
					numFileFail += 1
				else:
					if verbose:
						print("\t- Validated {0}".format(jsonSchemaURI))
					
					# Reverse mappings, needed later
					triggeringFeatures = list(map(lambda cFI: cFI.triggerAttribute, customFormatInstances))
					refSchemaSet[jsonSchemaURI] = traverseJSONSchema(jsonSchema,jsonSchemaURI,keys=triggeringFeatures)
					
					p_schemaHash[jsonSchemaURI] = schemaObj
					numFileOK += 1
			else:
				# This is here to capture cases where we wanted to validate an
				# unidentified schema for its correctness
				if verbose:
					print("\tIGNORE: validated, but schema in {0} has no id attribute".format(jsonSchemaFile),file=sys.stderr)
				errors.append({
					'reason': 'no_id',
					'description': "JSON Schema attributes '$id' (Draft06 onward) and 'id' (Draft04) are missing"
				})
				numFileIgnore += 1
		
		
		if verbose:
			print("\nSCHEMA VALIDATION STATS: loaded {0} schemas from {1} directories, ignored {2} schemas, failed {3} schemas and {4} directories".format(numFileOK,numDirOK,numFileIgnore,numFileFail,numDirFail))
		
			print("\nPASS 0.c: JSON schema set consistency checks")
		
		# TODO: augment refSchemaSet id2ElemId and keyRefs with
		# referenced schemas id2ElemId and keyRefs
		
		# Last, bootstrapping the extensions
		# Now, we check whether the declared foreign keys are pointing to loaded JSON schemas
		numSchemaConsistent = 0
		numSchemaInconsistent = 0
		for jsonSchemaURI , p_schema in p_schemaHash.items():
			jsonSchemaFile = p_schema['file']
			if verbose:
				print("* Checking {0}".format(jsonSchemaFile))
			customFormatInstances = p_schema['customFormatInstances']
			isValid = True
			if len(customFormatInstances) > 0:
				(id2ElemId , keyRefs , jp2val) = refSchemaSet[jsonSchemaURI]
				
				for cFI in customFormatInstances:
					if cFI.triggerAttribute in keyRefs:
						# Bootstrapping the schema
						# By default this is a no-op
						errors = cFI.bootstrap(refSchemaTuple=(id2ElemId , keyRefs[cFI.triggerAttribute] , self.refSchemaCache))
						if errors:
							if verbose:
								for error in errors:
									print("\t- ERROR: {}".format(error['description']),file=sys.stderr)
							
							p_schema['errors'].extend(errors)
							isValid = False
			
			if isValid:
				if verbose:
					print("\t- Consistent!")
				numSchemaConsistent += 1
			else:
				numSchemaInconsistent += 1
		
		if verbose:
			print("\nSCHEMA CONSISTENCY STATS: {0} schemas right, {1} with inconsistencies".format(numSchemaConsistent,numSchemaInconsistent))
		
		return len(self.schemaHash.keys())
		
	def getValidSchemas(self):
		return self.schemaHash
	
	# This method invalidates the different cached elements as much
	# as possible, 
	def invalidateCaches(self):
		p_schemasObj = self.getValidSchemas()
		
		for schemaObj in p_schemasObj.values():
			dynSchemaVal = schemaObj['customFormatInstances']
			for dynVal in dynSchemaVal:
				dynVal.invalidateCaches()
	
	# This method warms up the different cached elements as much
	# as possible, 
	def warmUpCaches(self,dynValList=None,verbose=None):
		if not dynValList:
			dynValList = []
			p_schemasObj = self.getValidSchemas()
			
			for schemaObj in p_schemasObj.values():
				dynValList.extend(schemaObj['customFormatInstances'])
			
		for dynVal in dynValList:
			dynVal.warmUpCaches()
	
	def doSecondPass(self,dynValList,verbose=None):
		secondPassOK = 0
		secondPassFails = 0
		secondPassErrors = {}
		
		# First, gather the list of contexts
		gatheredContexts = {}
		for dynVal in dynValList:
			dynContext = dynVal.getContext()
			if dynContext is not None:
				gatheredContexts.setdefault(dynVal.__class__.__name__,[]).append(dynContext)
		
		# We have to run this even when there is no gathered context
		# because there could be validators wanting to complain
		secondPassProcessed = set()
		secondPassFailed = set()
		for dynVal in dynValList:
			processed, failed, errors = dynVal.doSecondPass(gatheredContexts)
			secondPassProcessed.update(processed)
			secondPassFailed.update(failed)
			for error in errors:
				secondPassErrors.setdefault(error['file'],[]).append(error)
		
		secondPassFails = len(secondPassFailed)
		secondPassOK = len(secondPassProcessed) - secondPassFails
		
		return secondPassOK, secondPassFails, secondPassErrors
	
	def _resetDynamicValidators(self,dynValList,verbose=None):
		for dynVal in dynValList:
			dynVal.cleanup()
	
	@classmethod
	def GetNormalizedJSONHash(cls,json_data):
		# First, we serialize it in a reproducible way
		json_canon = json.dumps(json_data,sort_keys=True,indent=None,separators=(',',':'))
		
		return hashlib.sha1(json_canon.encode('utf-8')).hexdigest()
	
	def jsonValidate(self,*args,verbose=None):
		p_schemaHash = self.schemaHash
		
		# A two level hash, in order to check primary key restrictions
		PKvals = dict()
		
		# JSON validation stats
		numDirOK = 0
		numDirFail = 0
		numFilePass1OK = 0
		numFilePass1Ignore = 0
		numFilePass1Fail = 0
		numFilePass2OK = 0
		numFilePass2Fail = 0
		
		report = []
		dynSchemaSet = set()
		dynSchemaValList = []
		
		# First pass, check against JSON schema, as well as primary keys unicity
		if verbose:
			print("\nPASS 1: Schema validation and PK checks")
		iJsonPossible = -1
		jsonPossibles = list(args)
		for jsonPossible in jsonPossibles:
			iJsonPossible += 1
			jsonObj = None
			if isinstance(jsonPossible,dict):
				jsonObj = jsonPossible
				errors = jsonObj.get('errors')
				if errors is None:
					if verbose:
						print("\tIGNORE: cached JSON does not have the mandatory 'errors' attribute, so it cannot be processed")
					numFileIgnore += 1
					
					# For the report
					jsonObj.setDefault('errors',[{'reason': 'ignored', 'description': 'Programming error: uninitialized error structures'}])
					report.append(jsonObj)
					
					# Masking it for the pass 2 loop
					jsonPossibles[iJsonPossible] = None
					continue
				
				jsonDoc = jsonObj.get('json')
				if jsonDoc is None:
					if verbose:
						print("\tIGNORE: cached JSON does not have the mandatory 'json' attribute, so it cannot be processed")
					errors.append({
						'reason': 'ignored',
						'description': "Programming error: the cached json is missing"
					})
					numFileIgnore += 1
					
					# For the report
					report.append(jsonObj)
					
					# Masking it for the pass 2 loop
					jsonPossibles[iJsonPossible] = None
					continue
				
				jsonFile = jsonObj.setdefault('file','(inline)')
			elif os.path.isdir(jsonPossible):
				jsonDir = jsonPossible
				# It's a possible JSON directory, not a JSON file
				try:
					for relJsonFile in os.listdir(jsonDir):
						# Skipping hidden files / directories
						if relJsonFile[0]=='.':
							continue
						
						newJsonFile = os.path.join(jsonDir,relJsonFile)
						if os.path.isdir(newJsonFile) or '.json' in relJsonFile:
							jsonPossibles.append(newJsonFile)
					
					numDirOK += 1
				except IOError as ioe:
					if verbose:
						print("FATAL ERROR: Unable to open/process JSON directory {0}. Reason: {1}".format(jsonDir,ioe.strerror),file=sys.stderr)
					report.append({'file': jsonDir,'errors': [{'reason': 'fatal', 'description': 'Unable to open/process JSON directory'}]})
					numDirFail += 1
				finally:
					# Masking it for the pass 2 loop
					jsonPossibles[iJsonPossible] = None
				
				continue
			else:
				jsonFile = jsonPossible
				try:
					with open(jsonFile,mode="r",encoding="utf-8") as jHandle:
						if verbose:
							print("* Validating {0}".format(jsonFile))
						jsonDoc = json.load(jHandle)
						
				except IOError as ioe:
					if verbose:
						print("\t- ERROR: Unable to open file {0}. Reason: {1}".format(jsonFile,ioe.strerror),file=sys.stderr)
					# Masking it for the next loop
					report.append({'file': jsonFile,'errors': [{'reason': 'fatal', 'description': 'Unable to open/parse JSON file'}]})
					jsonPossibles[iJsonPossible] = None
					numFilePass1Fail += 1
					continue
				
				else:
					errors = []
					jsonObj = {
						'file': jsonFile,
						'json': jsonDoc,
						'errors': errors
					}
					# Upgrading for the next loop
					jsonPossibles[iJsonPossible] = jsonObj
			
			# Getting the schema id to locate the proper schema to validate against
			jsonRoot = jsonDoc['fair_tracks']  if 'fair_tracks' in jsonDoc  else jsonDoc
			
			jsonSchemaId = None
			for altSchemaKey in self.ALT_SCHEMA_KEYS:
				if altSchemaKey in jsonRoot:
					jsonSchemaId = jsonRoot[altSchemaKey]
					break
			
			if jsonSchemaId is not None:
				if jsonSchemaId in p_schemaHash:
					if verbose:
						print("\t- Using {0} schema".format(jsonSchemaId))
					
					schemaObj = p_schemaHash[jsonSchemaId]
					
					for customFormatInstance in schemaObj['customFormatInstances']:
						customFormatInstance.setCurrentJSONFilename(jsonFile)
					
					# Registering the dynamic validators to be cleaned up
					# when the validator finishes the session
					if jsonSchemaId not in dynSchemaSet:
						dynSchemaSet.add(jsonSchemaId)
						localDynSchemaVal = schemaObj['customFormatInstances']
						if localDynSchemaVal:
							# We reset them, in case they were dirty
							self._resetDynamicValidators(localDynSchemaVal)
							dynSchemaValList.extend(localDynSchemaVal)
					
					jsonSchema = schemaObj['schema']
					validator = schemaObj['validator']
					jsonObj['schema_hash'] = schemaObj['schema_hash']
					jsonObj['schema_id'] = jsonSchemaId
					
					cachedSchemasResolver = JSV.RefResolver(base_uri=jsonSchemaId, referrer=jsonSchema, store=self.refSchemaCache)
					
					valErrors = [ error  for error in validator(jsonSchema, format_checker = self.customFormatCheckerInstance,resolver = cachedSchemasResolver).iter_errors(jsonDoc) ]
					
					if len(valErrors) > 0:
						if verbose:
							print("\t- ERRORS:\n"+"\n".join(map(lambda se: "\t\tPath: {0} . Message: {1}".format("/"+"/".join(map(lambda e: str(e),se.path)),se.message) , valErrors))+"\n")
						for valError in valErrors:
							if isinstance(valError.validator_value,dict):
								schema_error_reason = valError.validator_value.get('reason','schema_error')
							else:
								schema_error_reason = 'schema_error'
							
							errPath = "/"+"/".join(map(lambda e: str(e),valError.path))
							errors.append({
								'reason': schema_error_reason,
								'description': "Path: {0} . Message: {1}".format(errPath,valError.message),
								'path': errPath
							})
						
						# Masking it for the next loop
						report.append(jsonPossibles[iJsonPossible])
						jsonPossibles[iJsonPossible] = None
						numFilePass1Fail += 1
					else:
						# Does the schema contain a PK declaration?
						isValid = True
						if verbose:
							print("\t- Validated!\n")
						numFilePass1OK += 1
					
				else:
					if verbose:
						print("\t- Skipping schema validation (schema with URI {0} not found)".format(jsonSchemaId))
					errors.append({
						'reason': 'schema_unknown',
						'description': "Schema with URI {0} was not loaded".format(jsonSchemaId)
					})
					# Masking it for the next loop
					report.append(jsonPossibles[iJsonPossible])
					jsonPossibles[iJsonPossible] = None
					numFilePass1Ignore += 1
			else:
				if verbose:
					print("\t- Skipping schema validation (no one declared for {0})".format(jsonFile))
				errors.append({
					'reason': 'no_id',
					'description': "No hint to identify the correct JSON Schema to be used to validate"
				})
				# Masking it for the next loop
				report.append(jsonPossibles[iJsonPossible])
				jsonPossibles[iJsonPossible] = None
				numFilePass1Ignore += 1
		
		#use Data::Dumper;
		#
		#print Dumper(\%PKvals),"\n";
		
		
		
		if dynSchemaValList:
			# Second pass, check foreign keys against gathered primary keys
			if verbose:
				print("PASS 2: additional checks (foreign keys and so)")
			self.warmUpCaches(dynSchemaValList,verbose)
			numFilePass2OK , numFilePass2Fail , secondPassErrors = self.doSecondPass(dynSchemaValList,verbose)
			# Reset the dynamic validators
			self._resetDynamicValidators(dynSchemaValList,verbose)
			
			#use Data::Dumper;
			#print Dumper(@jsonFiles),"\n";
			for jsonObj in jsonPossibles:
				if jsonObj is None:
					continue
				
				# Adding this survivor to the report
				report.append(jsonObj)
				jsonFile = jsonObj['file']
				if verbose:
					print("* Additional checks on {0}".format(jsonFile))
				
				errorList = secondPassErrors.get(jsonFile)
				if errorList:
					jsonObj['errors'].extend(errorList)
					if verbose:
						print("\t- ERRORS:")
						print("\n".join(map(lambda e: "\t\tPath: {0} . Message: {1}".format(e['path'],e['description']), errorList)))
				elif verbose:
					print("\t- Validated!")
		elif verbose:
			print("PASS 2: (skipped)")
		
		if verbose:
			print("\nVALIDATION STATS:\n\t- directories ({0} OK, {1} failed)\n\t- PASS 1 ({2} OK, {3} ignored, {4} error)\n\t- PASS 2 ({5} OK, {6} error)".format(numDirOK,numDirFail,numFilePass1OK,numFilePass1Ignore,numFilePass1Fail,numFilePass2OK,numFilePass2Fail))
		
		return report

class FairGTracksValidator(ExtensibleValidator):
	# This has been commented out, as we are following the format validation path
	CustomTypes = {
	#	'curie': CurieSearch.IsCurie,
	#	'term': OntologyTerm.IsTerm
	}

	CustomFormats = [
		CurieSearch,
		OntologyTerm
	]
	
	CustomValidators = {
		None: [
			CurieSearch,
			OntologyTerm,
			UniqueKey,
			PrimaryKey,
			ForeignKey
		]
	}
	
	def __init__(self,customFormats=CustomFormats, customTypes=CustomTypes, customValidators=CustomValidators, config=None):
		super().__init__(customFormats,customTypes,customValidators,config)
