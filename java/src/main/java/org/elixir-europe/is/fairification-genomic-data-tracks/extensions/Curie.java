package org.elixir_europe.is.fairification_genomic_data_tracks.extensions;

public class Curie {
	public final String id;
	public final String namespace;
	public final String name;
	public final String pattern;
	
	public Curie(String id, String namespace, String name, String pattern) {
		this.id = id;
		this.namespace = namespace;
		this.name = name;
		this.pattern = pattern;
	}
	
	public String toString() {
		return "("+id+","+namespace+","+name+","+pattern+")";
	}
}
