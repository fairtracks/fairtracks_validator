package org.elixir_europe.is.fairification_genomic_data_tracks.extensions;

import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

public class Curie {
	public final String id;
	public final String namespace;
	public final String name;
	public final String pattern;
	private Pattern compPattern;
	
	public Curie(String id, String namespace, String name, String pattern) {
		this.id = id;
		this.namespace = namespace;
		this.name = name;
		this.pattern = pattern;
		compPattern = null;
	}
	
	public String toString() {
		return "("+id+","+namespace+","+name+","+pattern+")";
	}
	
	public Pattern getPattern()
		throws PatternSyntaxException
	{
		if(compPattern==null) {
			compPattern = Pattern.compile(pattern);
		}
		
		return compPattern;
	}
}
