package org.elixir_europe.is.fairification_genomic_data_tracks;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.IOException;
import java.io.Reader;

import java.net.URI;

import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import java.net.URISyntaxException;

import org.everit.json.schema.Schema;
import org.everit.json.schema.ValidationException;
import org.everit.json.schema.loader.SchemaLoader;

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

/**
 * Hello world!
 *
 */
public class FairGTrackValidatorCli
{
	final class CachedJSONSchema {
		public final String id;
		public final JSONObject jsonSchema;
		public final File jsonSchemaFile;
		
		public CachedJSONSchema(String id,JSONObject jsonSchema,File jsonSchemaFile) {
			this.id = id;
			this.jsonSchema = jsonSchema;
			this.jsonSchemaFile = jsonSchemaFile;
		}
	}
	
	protected Validator p_schemaHash;
	protected Map<String,CachedJSONSchema> uriLoad;
	
	public FairGTrackValidatorCli(List<File> jsonSchemaFiles) {
		p_schemaHash = new Validator();
		
		uriLoad = cacheJSONSchemas(jsonSchemaFiles);
		loadJSONSchemas();
	}
	
	protected Map<String,CachedJSONSchema> cacheJSONSchemas(List<File> jsonSchemaFiles) {
		// Schema validation stats
		int numDirOK = 0;
		int numDirFail = 0;
		HashMap<String,CachedJSONSchema> uriLoad = new HashMap<>();
		int numFileOK = 0;
		int numFileIgnore = 0;
		int numFileFail = 0;
		
		System.out.println("PASS 0.0: JSON schema cache linking");
		System.out.flush();
		
		// It is done so, in order to avoid the ConcurrentModificationException
		for(int iJsonSchemaFile = 0; iJsonSchemaFile < jsonSchemaFiles.size(); iJsonSchemaFile++) {
			File jsonSchemaFile = jsonSchemaFiles.get(iJsonSchemaFile);
			if(jsonSchemaFile.isDirectory()) {
				// It's a possible JSON Schema directory, not a JSON Schema file
				Path jsonSchemaDir = jsonSchemaFile.toPath();
				try(DirectoryStream<Path> jsonSchemaDirStream = Files.newDirectoryStream(jsonSchemaDir)) {
					for(Path newJsonSchemaPath: jsonSchemaDirStream) {
						File newJsonSchemaFile = newJsonSchemaPath.toFile();
						if(newJsonSchemaFile.getName().charAt(0)!='.') {
							if(newJsonSchemaFile.isDirectory() || newJsonSchemaFile.getName().contains(".json")) {
								jsonSchemaFiles.add(newJsonSchemaFile);
							}
						}
					}
					numDirOK++;
				} catch(IOException ioe) {
					System.err.printf("FATAL ERROR: Unable to open JSON schema directory %s. Reason: %s\n",jsonSchemaFile.getPath(),ioe.getMessage());
					System.err.flush();
					numDirFail++;
				}
			} else {
				System.out.printf("* Analyzing schema %s\n",jsonSchemaFile.getPath());
				System.out.flush();

				try(
					InputStream jsonStream = new BufferedInputStream(new FileInputStream(jsonSchemaFile),1024*1024);
					Reader jsonReader = new InputStreamReader(jsonStream,"UTF-8");
				) {
					JSONTokener jt = new JSONTokener(jsonReader);
					JSONObject jsonSchema = new JSONObject(jt);
					
					String idKey = jsonSchema.has(ValidatedJSONSchema.NEW_ID_KEY) ? ValidatedJSONSchema.NEW_ID_KEY : ValidatedJSONSchema.ID_KEY;
					
					String jsonSchemaURI = jsonSchema.optString(idKey);
					if(jsonSchemaURI != null) {
						if(uriLoad.containsKey(jsonSchemaURI)) {
							numFileIgnore++;
							System.out.println("\t- Skipped due duplicate URI " + jsonSchemaURI);
						} else {
							numFileOK++;
							uriLoad.put(jsonSchemaURI,new CachedJSONSchema(jsonSchemaURI,jsonSchema,jsonSchemaFile));
							System.out.println("\t- Cached URI "+jsonSchemaURI);
						}
						System.out.flush();
					} else {
						System.err.printf("\tIGNORE: %s does not have the mandatory '$id' or 'id' attribute\n",jsonSchemaFile.getPath());
						System.err.flush();
						numFileIgnore++;
					}
				} catch(IOException ioe) {
					System.err.printf("FATAL ERROR: Unable to open schema file %s. Reason: %s\n",jsonSchemaFile.getPath(),ioe.getMessage());
					System.err.flush();
					numFileFail++;
				}
			}
		}
		
		System.out.printf("\nSCHEMA LINKING STATS: linked %d schemas from %d directories, %d schemas to be loaded, ignored %d files, failed %d schemas and %d directories\n",numFileOK,numDirOK,uriLoad.size(),numFileIgnore,numFileFail,numDirFail);
		System.out.flush();
		
		return uriLoad;
	}
	
	protected void loadJSONSchemas() {
		// Schema validation stats
		int numFileOK = 0;
		int numFileIgnore = 0;
		int numFileFail = 0;
		
		System.out.println("\nPASS 0.a: JSON schema loading and validation");
		System.out.flush();
		
		// Generate the map of cached schemas
		Map<URI,JSONObject> cachedSchemas = new HashMap<>();
		for(CachedJSONSchema cachedJ: uriLoad.values()) {
			try {
				cachedSchemas.put(new URI(cachedJ.id),cachedJ.jsonSchema);
			} catch(URISyntaxException use) {
				System.err.println("ERROR: Cached JSON Schema "+cachedJ.jsonSchemaFile.getPath()+" has as id an invalid URI: "+cachedJ.id);
				System.err.flush();
			}
		}
		
		// It is done so, in order to avoid the ConcurrentModificationException
		for(CachedJSONSchema cachedJ: uriLoad.values()) {
			File jsonSchemaFile = cachedJ.jsonSchemaFile;
			try {
				System.out.printf("* Loading schema %s\n",jsonSchemaFile.getPath());
				System.out.flush();
				ValidatedJSONSchema bSchemaDoc = p_schemaHash.addSchema(cachedJ.jsonSchema,jsonSchemaFile,cachedSchemas);
				System.out.printf("\t- Validated %s\n",bSchemaDoc.getId().toString());
				System.out.flush();
				for(String warning: bSchemaDoc.getWarnings()) {
					System.err.println("\tWARNING: "+warning);
					System.err.flush();
				}
				numFileOK++;
			} catch(ValidationException ve) {
				System.err.println("\t- ERRORS:");
				ve.getCausingExceptions().stream().forEach(se -> System.err.printf("\t\tPath: %s . Message: %s\n",se.getPointerToViolation(),se.getMessage()));
				System.err.flush();
				numFileFail++;
			} catch(SchemaRepeatedIdException srie) {
				System.err.println("\tERROR: "+srie.getMessage());
				System.err.flush();
				numFileFail++;
			} catch(SchemaNoIdException snie) {
				System.err.println("\tIGNORE: "+snie.getMessage());
				System.err.flush();
				numFileIgnore++;
			} catch(SchemaNoSchemaException snse) {
				System.err.println("\tIGNORE: "+snse.getMessage());
				System.err.flush();
				numFileIgnore++;
			} catch(UnsupportedSchemaException use) {
				System.err.println("\tIGNORE/FIXME: "+use.getMessage());
				System.err.flush();
				numFileIgnore++;
			}
		}

		System.out.printf("\nSCHEMA VALIDATION STATS: loaded %d schemas, ignored %d schemas, failed %d schemas\n",numFileOK,numFileIgnore,numFileFail);
		
		System.out.println("\nPASS 0.b: JSON schema set consistency checks");
		System.out.flush();
		
		// Now, we check whether the declared foreign keys are pointing to loaded JSON schemas
		int numSchemaConsistent = 0;
		int numSchemaInconsistent = 0;
		for(ValidatedJSONSchema p_schema: p_schemaHash.getSchemas()) {
			System.out.printf("* Checking %s\n",p_schema.getJsonSchemaSource());
			
			try {
				p_schemaHash.consistencyChecks(p_schema);
				System.out.println("\t- Consistent!");
				numSchemaConsistent ++;
			} catch(SchemaInconsistentException sie) {
				sie.getInconsistencies().forEach(incon -> System.err.println("\t FK ERROR: "+incon));
				numSchemaInconsistent++;
			}
		}
		
		System.out.printf("\nSCHEMA CONSISTENCY STATS: %d schemas right, %d with inconsistencies\n",numSchemaConsistent,numSchemaInconsistent);
	}
	
	public boolean isEmpty() {
		return p_schemaHash.isEmpty();
	}
	
	public void jsonValidate(List<File> jsonFiles) {
		// JSON validation stats
		int numDirOK = 0;
		int numDirFail = 0;
		int numFilePass1OK = 0;
		int numFilePass1Ignore = 0;
		int numFilePass1Fail = 0;
		int numFilePass2OK = 0;
		int numFilePass2Fail = 0;
		
		// First pass, check against JSON schema, as well as primary keys unicity
		System.out.println("\nPASS 1: Schema validation and PK checks");
		
		for(int iJsonFile = 0; iJsonFile < jsonFiles.size(); iJsonFile++) {
			File jsonFile = jsonFiles.get(iJsonFile);
			if(jsonFile.isDirectory()) {
				// It's a possible JSON directory, not a JSON file
				Path jsonDir = jsonFile.toPath();
				try(DirectoryStream<Path> jsonDirStream = Files.newDirectoryStream(jsonDir)) {
					for(Path newJsonPath: jsonDirStream) {
						File newJsonFile = newJsonPath.toFile();
						// Skipping hidden files / directories
						if(newJsonFile.getName().charAt(0)!='.') {
							if(newJsonFile.isDirectory() || newJsonFile.getName().contains(".json")) {
								jsonFiles.add(newJsonFile);
							}
						}
					}
					// Masking it for the pass 2 loop
					jsonFiles.set(iJsonFile,null);
					numDirOK++;
				} catch(IOException ioe) {
					System.err.printf("FATAL ERROR: Unable to open JSON directory %s. Reason: %s\n",jsonFile.getPath(),ioe.getMessage());
					System.err.flush();
					numDirFail++;
				}
			} else {
				System.out.printf("* Validating %s\n",jsonFile.getPath());
				System.out.flush();
				try {
					ValidableDoc bDoc = ValidableDoc.parseFile(jsonFile);
					try {
						System.out.printf("\t- Using %s schema\n",bDoc.getJsonSchemaId());
						System.out.flush();
						p_schemaHash.validatePass1(bDoc);
						System.out.println("\t- Validated!\n");
						System.out.flush();
						numFilePass1OK++;
					} catch(ValidableDocNoSchemaIdException bdnsie) {
						System.out.println("\t- "+bdnsie.getMessage());
						// Masking it for the next loop
						jsonFiles.set(iJsonFile,null);
						numFilePass1Ignore++;
					} catch(OrphanValidableDocException obde) {
						System.out.println("\t- "+obde.getMessage());
						// Masking it for the next loop
						jsonFiles.set(iJsonFile,null);
						numFilePass1Ignore++;
					} catch(ValidableDocUnmatchingSchemaException bduse) {
						System.out.println("\t- ASSERTION ERROR: "+bduse.getMessage());
						// Masking it for the next loop
						jsonFiles.set(iJsonFile,null);
						numFilePass1Fail++;
					} catch(ValidationException ve) {
						System.err.println("\t- ERRORS:");
						ve.getCausingExceptions().stream().forEach(se -> System.err.printf("\t\tPath: %s . Message: %s\n",se.getPointerToViolation(),se.getMessage()));
						System.err.flush();
						//Masking it for the next loop
						jsonFiles.set(iJsonFile,null);
						numFilePass1Fail++;
						ve.printStackTrace();
					} catch(SchemaDuplicatedPrimaryKeyException sdpke) {
						System.out.printf("\t- Using %s schema\n",bDoc.getJsonSchemaId());
						System.out.flush();
						Collection<SchemaDuplicatedPrimaryKeyException> inconsistencies = sdpke.getInconsistencies();
						if(inconsistencies!=null) {
							inconsistencies.forEach(incon -> System.err.println("\t PK ERROR: "+incon.getMessage()));
						} else {
							System.err.println("\t PK ERROR: "+sdpke.getMessage());
						}
						System.err.flush();
						//Masking it for the next loop
						jsonFiles.set(iJsonFile,null);
						numFilePass1Fail++;
					}
				} catch(IOException ioe) {
					System.err.printf("\t- ERROR: Unable to open file %s. Reason: %s\n",jsonFile.getPath(),ioe.getMessage());
					System.err.flush();
					// Masking it for the next loop
					jsonFiles.set(iJsonFile,null);
					numFilePass1Fail++;
				}
			}
		}
		
		// Second pass, check foreign keys against gathered primary keys
		System.out.println("PASS 2: foreign keys checks");
		
		for(File jsonFile: jsonFiles) {
			if(jsonFile!=null) {
				System.out.printf("* Checking FK on %s\n",jsonFile.getPath());
				System.out.flush();
				try {
					ValidableDoc bDoc = ValidableDoc.parseFile(jsonFile);
					try {
						p_schemaHash.validatePass2(bDoc);
						System.out.printf("\t- Using %s schema\n",bDoc.getJsonSchemaId());
						System.out.println("\t- Validated!\n");
						System.out.flush();
						numFilePass2OK++;
					} catch(ValidableDocNoSchemaIdException bdnsie) {
						System.out.println("\t- ASSERTION ERROR: "+bdnsie.getMessage());
						numFilePass2Fail++;
					} catch(OrphanValidableDocException obde) {
						System.out.println("\t- ASSERTION ERROR: "+obde.getMessage());
						numFilePass2Fail++;
					} catch(SchemaMissingForeignKeySchemaException smfkse) {
						System.out.printf("\t- Using %s schema\n",bDoc.getJsonSchemaId());
						System.out.flush();
						Collection<SchemaMissingForeignKeySchemaException> inconsistencies = smfkse.getInconsistencies();
						if(inconsistencies!=null) {
							inconsistencies.forEach(incon -> System.err.println(((incon instanceof SchemaMissingForeignKeyNoDocumentsException) ? "\t FK ERROR: ":"\t ASSERTION ERROR: ")+incon.getMessage()));
						} else {
							System.err.println(((smfkse instanceof SchemaMissingForeignKeyNoDocumentsException) ? "\t FK ERROR: ":"\t ASSERTION ERROR: ")+smfkse.getMessage());
						}
						System.err.flush();
						numFilePass2Fail++;
					}
				} catch(IOException ioe) {
					System.err.printf("\t- ERROR: Unable to open file %s. Reason: %s\n",jsonFile.getPath(),ioe.getMessage());
					System.err.flush();
					numFilePass2Fail++;
				}
			}
		}
		
		System.out.printf("\nVALIDATION STATS:\n\t- directories (%d OK, %d failed)\n\t- PASS 1 (%d OK, %d ignored, %d error)\n\t- PASS 2 (%d OK, %d error)\n",numDirOK,numDirFail,numFilePass1OK,numFilePass1Ignore,numFilePass1Fail,numFilePass2OK,numFilePass2Fail);
	}
	
	public final static void main( String[] args )
	{
		if(args.length > 0) {
			List<File> jsonFiles = Arrays.stream(args).map(jsonPath -> new File(jsonPath)).collect(Collectors.toCollection(ArrayList::new));
			File jsonSchemaPath = jsonFiles.remove(0);
			List<File> jsonSchemaFiles = new ArrayList<File>();
			jsonSchemaFiles.add(jsonSchemaPath);
			FairGTrackValidatorCli vcli = new FairGTrackValidatorCli(jsonSchemaFiles);
			
			if(!jsonFiles.isEmpty()) {
				if(vcli.isEmpty()) {
					System.err.println("FATAL ERROR: No schema was successfuly loaded. Exiting...");
					System.exit(1);
				}
				
				vcli.jsonValidate(jsonFiles);
			}
		} else {
			System.err.println("Usage: jsonValidate {JSON schema} {JSON file}*");
			System.exit(1);
		}
	}
}
