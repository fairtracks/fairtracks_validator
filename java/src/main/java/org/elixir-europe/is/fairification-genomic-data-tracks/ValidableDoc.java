package org.elixir_europe.is.fairification_genomic_data_tracks;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.IOException;
import java.io.Reader;

import java.net.URI;
import java.net.URISyntaxException;

import java.util.ArrayList;
import java.util.Collection;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.stream.Collectors;

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

public class ValidableDoc {
	protected final static String PARENT_SCHEMA_KEY = "fair_tracks";
	protected final static String SCHEMA_KEY = "$schema";
	protected final static String[] ALT_SCHEMA_KEYS = {
		"@schema",
		"_schema",
		SCHEMA_KEY
	};
	
	protected static final Pattern jStepPat = Pattern.compile("^([^\\[]+)\\[(0|[1-9][0-9]+)?\\]$");
	
	protected JSONObject jsonDoc;
	protected String jsonSource;
	protected URI jsonSchemaId;
	
	public ValidableDoc(JSONObject jsonDoc) {
		this(jsonDoc,"<unknown>");
	}
	
	public ValidableDoc(JSONObject jsonDoc,String jsonSource) {
		this.jsonDoc = jsonDoc;
		this.jsonSource = jsonSource;
		
		jsonSchemaId = null;
		JSONObject parent = jsonDoc.optJSONObject(PARENT_SCHEMA_KEY);
		if(parent == null) {
			parent = jsonDoc;
		}
		String jsonSchemaIdStr = null;
		for(final String altSchemaKey: ALT_SCHEMA_KEYS) {
			jsonSchemaIdStr = parent.optString(altSchemaKey,null);
			if(jsonSchemaIdStr!=null) {
				break;
			}
		}
		if(jsonSchemaIdStr != null) {
			try{
				jsonSchemaId = new URI(jsonSchemaIdStr);
			} catch(URISyntaxException use) {
				// IgnoreIt(R)
			}
		}
	}
	
	public static ValidableDoc parseFile(File jsonFile)
		throws IOException
	{
		try(
			InputStream jsonStream = new BufferedInputStream(new FileInputStream(jsonFile),1024*1024);
			Reader jsonReader = new InputStreamReader(jsonStream,"UTF-8");
		) {
			JSONTokener jt = new JSONTokener(jsonReader);
			JSONObject jsonDoc = new JSONObject(jt);
			String jsonSource = jsonFile.getAbsolutePath();
			return new ValidableDoc(jsonDoc,jsonSource);
		}
	}
	
	public URI getJsonSchemaId() {
		return jsonSchemaId;
	}
	
	public String getJsonSource() {
		return jsonSource;
	}
	
	public JSONObject getJsonDoc() {
		return jsonDoc;
	}
	
	protected Collection<String> materializeJPath(String jPath) {
		Collection<Object> objectives = new ArrayList<Object>();
		objectives.add(jsonDoc);
		
		String[] jSteps = (jPath.length() ==0 || jPath.equals('.')) ? new String[] { null } : jPath.split("\\.");
		for(String jStep: jSteps) {
			// Fail fast
			if(objectives.isEmpty())  break;
			
			Collection<Object> newObjectives = new ArrayList<Object>();
			boolean isArray = false;
			Integer arrayIndex = null;
			if(jStep!=null) {
				Matcher jStepMatch = jStepPat.matcher(jStep);
				if(jStepMatch.find()) {
					isArray = true;
					String strIndex = jStepMatch.group(2);
					if(strIndex!=null) {
						arrayIndex = Integer.valueOf(strIndex);
					}
					jStep = jStepMatch.group(1);
				}
			}
			for(Object objective: objectives) {
				boolean isAvailable = false;
				Object value = null;
				if(jStep!=null) {
					if(objective instanceof JSONObject) {
						JSONObject obj = (JSONObject)objective;
						if(obj.has(jStep)) {
							value = obj.get(jStep);
							isAvailable = true;
						}
					//} else {
					//	// Failing
					//	return null;
					}
				} else {
					value = objective;
					isAvailable = true;
				}
				
				if(isAvailable) {
					if(value instanceof JSONArray) {
						JSONArray aValue = (JSONArray)value;
						if(arrayIndex!=null) {
							if(arrayIndex >= 0 && arrayIndex < aValue.length()) {
								newObjectives.add(aValue.opt(arrayIndex));
							//} else {
							//	return null;
							}
						} else {
							aValue.iterator().forEachRemaining(newObjectives::add);
						}
					} else {
						newObjectives.add(value);
					}
				//} else {
				//	// Failing
				//	return null;
				}
			}
			
			objectives = newObjectives;
		}
		
		// Flattening it (we return a reference to a list of atomic values)
		Collection<String> strObjectives = objectives.stream().map(objective -> objective.toString()).collect(Collectors.toCollection(ArrayList::new));
		
		return strObjectives;
	}
	
	// It fetches the values from a JSON, based on the given paths to the members of the key
	public Collection<Collection<String>> getKeyValues(Collection<String> p_members) {
		return p_members.stream().map(member -> materializeJPath(member)).collect(Collectors.toCollection(ArrayList::new));
	}
}
