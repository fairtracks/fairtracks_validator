package org.elixir_europe.is.fairification_genomic_data_tracks.extensions;

import java.io.File;
import java.io.IOException;

import java.net.URI;
import java.net.URISyntaxException;

import java.sql.SQLException;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

import static java.util.Collections.emptyList;

import javax.xml.parsers.ParserConfigurationException;

import org.everit.json.schema.ContextualFormatValidator;

import org.freedesktop.BaseDirectory;

import org.xml.sax.SAXException;

public class CurieFormat
	implements ContextualFormatValidator
{
	public enum MatchType {
		CANONICAL,
		LOOSE,
		BASIC
	}
	
	public final static String DEFAULT_FORMAT_NAME = "curie";
	
	private final static String CACHE_PATH = "CURIE_cache.sqlite3";
	private static CurieCache CurCache = null;
	private final static CurieCache GetCurieCache()
		throws SQLException, IOException, ParserConfigurationException, SAXException
	{
		if(CurCache==null) {
			File cacheDir = new File(BaseDirectory.get(BaseDirectory.XDG_CACHE_HOME), "es.elixir.jsonValidator");
			
			if(cacheDir.exists()) {
				if(!cacheDir.isDirectory()) {
					throw new IOException(String.format("Cache path '%s' already exists, and it is not a directory",cacheDir.getAbsolutePath()));
				}
			} else if(!cacheDir.mkdirs()) {
				throw new IOException(String.format("Cache path '%s' could not be created",cacheDir.getAbsolutePath()));
			}
			
			CurCache = new CurieCache(new File(cacheDir, CACHE_PATH));
		}
		
		return CurCache;
	}
	
	private final static String MATCHTYPE_ATTR = "matchType";
	private final static String NAMESPACE_ATTR = "namespace";
	
	@Override
	public Optional<String> validate(final String subject, final Map<String, Object> unprocessedProperties) {
		MatchType matchType = MatchType.CANONICAL;
		
		if(unprocessedProperties.containsKey(MATCHTYPE_ATTR)) {
			String matchTypeStr = null;
			try {
				matchTypeStr = (String)unprocessedProperties.get(MATCHTYPE_ATTR);
			} catch(ClassCastException cce) {
				return Optional.of("'matchType' is not containing a string");
			}
			switch(matchTypeStr) {
				case "canonical":
					matchType = MatchType.CANONICAL;
					break;
				case "loose":
					matchType = MatchType.LOOSE;
					break;
				case "basic":
					matchType = MatchType.BASIC;
					break;
				default:
					return Optional.of(String.format("unknown 'matchType' \"%s\" in JSON Schema", subject));
			}
		}
		
		List<String> nslist = emptyList();
		if(unprocessedProperties.containsKey(NAMESPACE_ATTR)) {
			try {
				nslist = (List<String>) unprocessedProperties.get(NAMESPACE_ATTR);
			} catch(ClassCastException cce) {
				return Optional.of(String.format("property '%s' from JSON Schema should be an array of strings",NAMESPACE_ATTR));
			}
		}
		
		CurieCache cache = null;
		try {
			cache = GetCurieCache();
		} catch(Exception e) {
			return Optional.of("ERROR initializing CURIE cache: " + e.getMessage());
		}
		
		URI parsed = null;
		
		try {
			parsed = new URI(subject);
		} catch(URISyntaxException use) {
			if(matchType != MatchType.LOOSE) {
				return Optional.of(String.format("Incorrect URI '%s' (only acceptable in loose match type)",subject));
			}
		}
		
		// Trying to decide the matching mode
		String prefix = null;
		if(parsed!=null) {
			prefix = parsed.getScheme();
			if(prefix != null) {
				// Should we internally promote the matchType?
				if(prefix.length() > 0 && matchType == MatchType.LOOSE) {
					matchType = MatchType.CANONICAL;
				} else {
					prefix = null;
				}
			}
		}
		
		boolean found = false;
		switch(matchType) {
			case BASIC:
				// Basic mode is like canonical, but without querying identifiers.org cache
				found = nslist.contains(prefix);
				if(!found) {
					return Optional.of(String.format("The namespace %s is not in the list of the accepted ones: %s",prefix,String.join(", ",nslist)));
				}
				break;
			case LOOSE:
				if(nslist.size()>0) {
					boolean noneInCache = true;
					for(String namespace: nslist) {
						if(cache.containsKey(namespace)) {
							noneInCache = false;
							Curie curie = cache.get(namespace);
							
							// Looking for a match
							Pattern pat = null;
							try {
								pat = curie.getPattern();
							} catch(PatternSyntaxException pse) {
								return Optional.of(String.format("Pattern '%s' got from '%s' (identifiers.org) is bad-formed",curie.pattern,namespace));
							}
							if(pat.matcher(subject).matches()) {
								found = true;
								return Optional.empty();
							}
						}
					}
					
					if(noneInCache) {
						return Optional.of(String.format("No namespace from '%s' was found in identifiers.org cache",String.join(", ",nslist)));
					}
				} else {
					return Optional.of("In 'loose' mode, at least one namespace must be declared");
				}
				break;
			default:
				if(prefix==null) {
					return Optional.of("In 'canonical' mode, the value must be prefixed by the namespace");
				}
				
				// Searching in canonical mode. To do that, we have to remove the prefix
				String valToVal = parsed.getSchemeSpecificPart();
				
				// The case where the namespace list is empty
				if(nslist.size() > 0 && !nslist.contains(prefix)) {
					return Optional.of(String.format("The namespace %s is not in the list of the accepted ones: %s",prefix,String.join(", ",nslist)));
				}
				
				if(cache.containsKey(prefix)) {
					Curie curie = cache.get(prefix);
					
					Pattern pat = null;
					try {
						pat = curie.getPattern();
					} catch(PatternSyntaxException pse) {
						return Optional.of(String.format("Pattern '%s' got from '%s' (identifiers.org) is bad-formed",curie.pattern,prefix));
					}
					found = pat.matcher(valToVal).matches() || pat.matcher(subject).matches();
				} else {
					return Optional.of(String.format("The namespace %s was not found in identifiers.org cache",prefix));
				}
		}
		
		return found ? Optional.empty() : Optional.of(String.format("Match failed for CURIE %s",subject));
	}
	
	@Override
	public String formatName() {
		return DEFAULT_FORMAT_NAME;
	}
}
