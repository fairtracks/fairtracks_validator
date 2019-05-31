package org.elixir_europe.is.fairification_genomic_data_tracks.extensions;

import java.io.File;
import java.io.InputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;

import java.math.BigInteger;

import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.net.URLDecoder;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import static java.util.Collections.emptyList;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import javax.xml.bind.DatatypeConverter;

import org.eclipse.rdf4j.model.impl.SimpleValueFactory;
import org.eclipse.rdf4j.model.IRI;
import org.eclipse.rdf4j.model.Value;

import org.eclipse.rdf4j.query.TupleQuery;
import org.eclipse.rdf4j.query.TupleQueryResult;
import org.eclipse.rdf4j.query.BindingSet;
import org.eclipse.rdf4j.query.QueryLanguage;

import org.eclipse.rdf4j.RDF4JException;

import org.eclipse.rdf4j.repository.config.RepositoryConfig;
import org.eclipse.rdf4j.repository.config.RepositoryImplConfig;

import org.eclipse.rdf4j.repository.manager.LocalRepositoryManager;
import org.eclipse.rdf4j.repository.manager.RepositoryManager;
import org.eclipse.rdf4j.repository.manager.RepositoryInfo;

import org.eclipse.rdf4j.repository.Repository;
import org.eclipse.rdf4j.repository.RepositoryConnection;

import org.eclipse.rdf4j.repository.sail.SailRepository;

import org.eclipse.rdf4j.repository.sail.config.SailRepositoryConfig;

import org.eclipse.rdf4j.rio.RDFFormat;

import org.eclipse.rdf4j.sail.config.SailImplConfig;

import org.eclipse.rdf4j.sail.nativerdf.config.NativeStoreConfig;

import org.eclipse.rdf4j.sail.nativerdf.NativeStore;

import org.everit.json.schema.ContextualFormatValidator;

import org.freedesktop.BaseDirectory;

public class TermFormat
	implements ContextualFormatValidator
{
	public enum MatchType {
		EXACT,
		SUFFIX,
		LABEL
	}
	
	public final static String DEFAULT_FORMAT_NAME = "term";
	
	// These are the attributes expected in the JSON Schema
	private final static String ONTOLOGY_ATTR = "ontology";
	private final static String MATCHTYPE_ATTR = "matchType";
	private final static String ANCESTORS_ATTR = "ancestors";
	
	private final static String ONTOLOGY_MANAGER_PATH = "RDF4J_NATIVE_RDF";
	
	private final static String QUERY_PLACEHOLDER = "q";
	private final static String QUERY_ANCESTOR_PLACEHOLDER = "a";
	private final static String RES_BINDING_NAME = "res";
	
	private final static String LABEL_MATCH_SPARQL =
		"SELECT (?x AS ?res) WHERE {\n"+
		"?x rdfs:label ?q .\n" +
		"{ ?x rdf:type owl:Class }\n"+
		"UNION\n"+
		"{ ?x rdf:type rdfs:Class } .\n"+
		"} ";
	
	private final static String IRI_SUFFIX_MATCH_SPARQL =
		"SELECT (?x AS ?res) WHERE {\n"+
		"{ ?x rdf:type owl:Class }\n"+
		"UNION\n"+
		"{ ?x rdf:type rdfs:Class }\n"+
		"FILTER strends(str(?x),?q) .\n"+
		"} ";

	private final static String IRI_MATCH_SPARQL =
		"SELECT (?q AS ?res) WHERE {\n"+
		"{ ?q rdf:type owl:Class }\n"+
		"UNION\n"+
		"{ ?q rdf:type rdfs:Class }\n"+
		"} ";
	
	private final static SimpleValueFactory SVF;
	private static LocalRepositoryManager Manager;
	private static Map<String,Repository> OntologyRepoMap;
	private static Map<MatchType,String> SPARQLMatchMap;
	static {
		Manager = null;
		SVF = SimpleValueFactory.getInstance();
		OntologyRepoMap = new HashMap<>();
		
		// Initializing needed query matching
		SPARQLMatchMap = new HashMap<>();
		SPARQLMatchMap.put(MatchType.EXACT,IRI_MATCH_SPARQL);
		SPARQLMatchMap.put(MatchType.SUFFIX,IRI_SUFFIX_MATCH_SPARQL);
		SPARQLMatchMap.put(MatchType.LABEL,LABEL_MATCH_SPARQL);
	};
	
	private final static RepositoryManager GetOntologyManager()
		throws IOException
	{
		if(Manager==null) {
			File cacheDir = new File(BaseDirectory.get(BaseDirectory.XDG_CACHE_HOME), "es.elixir.jsonValidator");
			
			File ontologyManagerDir = new File(cacheDir, ONTOLOGY_MANAGER_PATH);
			
			if(ontologyManagerDir.exists()) {
				if(!ontologyManagerDir.isDirectory()) {
					throw new IOException(String.format("Ontology manager path '%s' already exists, and it is not a directory",ontologyManagerDir.getAbsolutePath()));
				}
			} else if(!ontologyManagerDir.mkdirs()) {
				throw new IOException(String.format("Ontology manager path '%s' could not be created",ontologyManagerDir.getAbsolutePath()));
			}
			
			Manager = new LocalRepositoryManager(ontologyManagerDir);
			Manager.initialize();
		}
		
		return Manager;
	}
	
	// This manages redirects, inspired in https://stackoverflow.com/a/26046079
	private final static HttpURLConnection GetURLConnection(URL resourceUrl)
		throws IOException
	{
		HttpURLConnection conn;
		Map<String, Integer> visited = new HashMap<>();

		while(true) {
			String url = null;
			String proto = resourceUrl.getProtocol();
			switch(proto) {
				case "http":
				case "https":
				case "ftp":
					url = resourceUrl.toExternalForm();
					int times = visited.compute(url, (key, count) -> count == null ? 1 : count + 1);
					
					if (times > 3) {
						throw new IOException("Stuck in redirect loop in URL "+url);
					}
					break;
				default:
					throw new IOException("Unknown protocol '"+proto+"'");
			}
			
			conn = (HttpURLConnection) resourceUrl.openConnection();
			
			//conn.setConnectTimeout(15000);
			//conn.setReadTimeout(15000);
			conn.setInstanceFollowRedirects(false);   // Make the logic below easier to detect redirections
			//conn.setRequestProperty("User-Agent", "Mozilla/5.0...");
			
			switch(conn.getResponseCode()) {
				case HttpURLConnection.HTTP_MOVED_PERM:
				case HttpURLConnection.HTTP_MOVED_TEMP:
					String location = conn.getHeaderField("Location");
					location = URLDecoder.decode(location, "UTF-8");
					
					conn.disconnect();
					
					URL base = resourceUrl;               
					URL next = new URL(base, location);  // Deal with relative URLs
					resourceUrl = next;
					continue;
			}
			break;
		}
		
		return conn;
	}
	
	private final static Repository GetOntologyRepo(String ontoStr)
		throws IOException, NoSuchAlgorithmException
	{
		Repository repo = null;
		
		if(OntologyRepoMap.containsKey(ontoStr)) {
			repo = OntologyRepoMap.get(ontoStr);
		} else {
			RepositoryManager manager = GetOntologyManager();
			
			MessageDigest md = MessageDigest.getInstance("SHA-256");
			byte[] repByteId = md.digest(ontoStr.getBytes("UTF-8"));
			String repId = DatatypeConverter.printHexBinary(repByteId);
			
			RepositoryInfo repInfo = manager.getRepositoryInfo(repId);
			if(repInfo == null) {
				// create a configuration for the SAIL stack
				SailImplConfig backendConfig = new NativeStoreConfig();
				// create a configuration for the repository implementation
				RepositoryImplConfig repositoryTypeSpec = new SailRepositoryConfig(backendConfig);
				
				RepositoryConfig repConfig = new RepositoryConfig(repId, repositoryTypeSpec);
				manager.addRepositoryConfig(repConfig);
				
				repInfo = manager.getRepositoryInfo(repId);
			}
			
			repo = manager.getRepository(repId);
			
			if(!repo.isInitialized()) {
				repo.init();
			}
			
			URL ontoURL = new URL(ontoStr);
			try(RepositoryConnection con = repo.getConnection()) {
				if(con.isEmpty()) {
					HttpURLConnection ontoConn = GetURLConnection(ontoURL);
					try(InputStream ontoIS = ontoConn.getInputStream()) {
						con.add(ontoIS, ontoStr, RDFFormat.RDFXML);
					} finally {
						ontoConn.disconnect();
					}
				}
			} catch(RDF4JException e) {
				// handle exception. This catch-clause is
				// optional since rdf4jException is an unchecked exception
				throw e;
			} catch(IOException e) {
				// handle io exception
				throw e;
			}
			
			// Saving it for later use
			OntologyRepoMap.put(ontoStr,repo);
		}
		
		return repo;
	}
	
	
	private final static String ANCESTORS_SPARQL =
		"SELECT (?a AS ?res) WHERE {\n"+
		"?q rdfs:subClassOf* ?a"+
		"} ";
	
	
	protected Optional<String> validate(final String subject, MatchType matchType, List<String> ontologies, List<String> ancestors) {
		// Checking for each ontology
		for(String ontologyStr: ontologies) {
			try {
				Repository repo = GetOntologyRepo(ontologyStr);
				String matchQuery = SPARQLMatchMap.get(matchType);
				
				try(RepositoryConnection con = repo.getConnection()) {
					TupleQuery tupleQuery = con.prepareTupleQuery(QueryLanguage.SPARQL, matchQuery);
					
					// We are working with IRIs only on exact match
					if(matchType == MatchType.EXACT) {
						tupleQuery.setBinding(QUERY_PLACEHOLDER,SVF.createIRI(subject));
					} else {
						tupleQuery.setBinding(QUERY_PLACEHOLDER,SVF.createLiteral(subject));
					}
					
					Set<IRI> foundTerms = null;
					try(TupleQueryResult tupleRes = tupleQuery.evaluate()) {
						if(tupleRes.hasNext()) {
							// Do next task only when there are ancestors to be validated
							if(ancestors.size() > 0) {
								foundTerms = new HashSet<>();
								do {
									BindingSet bindingSet = tupleRes.next();
									
									Value val = bindingSet.getValue(RES_BINDING_NAME);
									
									// We need the IRI to issue the query of the ancestors
									IRI iriVal;
									if(val instanceof IRI) {
										iriVal = (IRI)val;
									} else {
										iriVal = SVF.createIRI(val.stringValue());
									}
									foundTerms.add(iriVal);
								} while(tupleRes.hasNext());
							} else {
								// Term has been validated
								return Optional.empty();
							}
						}
					}
					
					if(foundTerms != null) {
						// If we are here is to check the validity of possible ancestors
						TupleQuery iriQuery = con.prepareTupleQuery(QueryLanguage.SPARQL, IRI_MATCH_SPARQL);
						for(IRI foundTerm: foundTerms) {
							iriQuery.setBinding(QUERY_PLACEHOLDER,foundTerm);
							for(String ancestor: ancestors) {
								// We are working with IRIs only on exact match
								iriQuery.setBinding(QUERY_ANCESTOR_PLACEHOLDER,SVF.createIRI(ancestor));
								try(TupleQueryResult iriRes = iriQuery.evaluate()) {
									if(iriRes.hasNext()) {
										// Term has been validated
										return Optional.empty();
									}
								}
							}
						}
					}
				//} catch(RDF4JException e) {
				//	// handle exception. This catch-clause is
				//	// optional since rdf4jException is an unchecked exception
				//	throw e;
				}
			} catch(Exception e) {
				StringWriter sw = new StringWriter();
				PrintWriter pw = new PrintWriter(sw);
				e.printStackTrace(pw);
				pw.flush();
				pw.close();
				
				return Optional.of(String.format("UNEXPECTED ERROR due an exception: %s\n%s",e.getMessage(),sw.getBuffer()));
			}
		}
		
		// No match with the constraints
		if(ancestors.size() > 0) {
			return Optional.of(String.format("Term %s , forced to have ancestors %s , was not found in these ontologies: %s",subject,String.join(" , ",ancestors),String.join(" , ",ontologies)));
		} else {
			return Optional.of(String.format("Term %s was not found in these ontologies: %s",subject,String.join(" , ",ontologies)));
		}
	}
	
	@Override
	public Optional<String> validate(final String subject, final Map<String, Object> unprocessedProperties) {
		// Early check
		if(!unprocessedProperties.containsKey(ONTOLOGY_ATTR)) {
			return Optional.of("format \""+DEFAULT_FORMAT_NAME+"\" requires attribute '"+ONTOLOGY_ATTR+"', and it does not appear in the JSON Schema");
		}
		
		// Getting the list of ontologies
		List<String> ontlist = emptyList();
		try {
			Object ontObj = unprocessedProperties.get(ONTOLOGY_ATTR);
			if(ontObj instanceof String) {
				ontlist = new ArrayList<>();
				ontlist.add((String)ontObj);
			} else if(ontObj instanceof List) {
				ontlist = (List<String>) ontObj;
			} else {
				return Optional.of(String.format("property '%s' from JSON Schema should be a string or an array of strings",ONTOLOGY_ATTR));
			}
		} catch(ClassCastException cce) {
			return Optional.of(String.format("Problems while casting value from property '%s'",ONTOLOGY_ATTR));
		}
		
		if(ontlist.size() > 0) {
			// Checking whether the ontologies are correct URLs
			for(String ontologyStr: ontlist) {
				try {
					URL ontoURL = new URL(ontologyStr);
					String proto = ontoURL.getProtocol();
					switch(proto) {
						case "http":
						case "https":
						case "ftp":
							// Good ones, follow
							break;
						default:
							// Unrecognized ones, complain
							return Optional.of("Ontology '"+ontologyStr+"' is not public available");
					}
				} catch(IOException ioe) {
					return Optional.of(String.format("'%s' is not a valid ontology URL",ontologyStr));
				}
			}
		} else {
			return Optional.of(String.format("Attribute '%s' does not contain any ontology",ONTOLOGY_ATTR));
		}
		
		// Getting the optional list of ancestors to check
		List<String> ancestors = emptyList();
		if(unprocessedProperties.containsKey(ANCESTORS_ATTR)) {
			Object ancObj = unprocessedProperties.get(ANCESTORS_ATTR);
			if(ancObj != null) {
				try {
					if(ancObj instanceof String) {
						ancestors = new ArrayList<>();
						ancestors.add((String)ancObj);
					} else if(ancObj instanceof List) {
						ancestors = (List<String>) ancObj;
					} else {
						return Optional.of(String.format("property '%s' from JSON Schema should be a string or an array of strings",ANCESTORS_ATTR));
					}
				} catch(ClassCastException cce) {
					return Optional.of(String.format("Problems while casting value from property '%s'",ANCESTORS_ATTR));
				}
			}
		}
		
		// Getting the current matchtype
		MatchType matchType = MatchType.EXACT;
		
		if(unprocessedProperties.containsKey(MATCHTYPE_ATTR)) {
			String matchTypeStr = null;
			try {
				matchTypeStr = (String)unprocessedProperties.get(MATCHTYPE_ATTR);
			} catch(ClassCastException cce) {
				return Optional.of("'matchType' is not containing a string");
			}
			switch(matchTypeStr) {
				case "exact":
					matchType = MatchType.EXACT;
					break;
				case "suffix":
					matchType = MatchType.SUFFIX;
					break;
				case "label":
					matchType = MatchType.LABEL;
					break;
				default:
					return Optional.of(String.format("unknown 'matchType' \"%s\" in JSON Schema", subject));
			}
		}
		
		return validate(subject,matchType,ontlist,ancestors);
	}
	
	@Override
	public String formatName() {
		return DEFAULT_FORMAT_NAME;
	}
}
