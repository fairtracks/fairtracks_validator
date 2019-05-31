package org.elixir_europe.is.fairification_genomic_data_tracks;

public class GenericSchemaException
	extends Exception
{
	protected String jsonSchemaSource;
	public GenericSchemaException(String jsonSchemaSource) {
		this.jsonSchemaSource = jsonSchemaSource;
	}
	
	@Override
	public String getMessage() {
		return String.format("unspecified error related to schema in %s",jsonSchemaSource);
	}
}
