package org.elixir_europe.is.fairification_genomic_data_tracks;

public class SchemaNoIdException
	extends GenericSchemaException
{
	public SchemaNoIdException(String jsonSchemaSource) {
		super(jsonSchemaSource);
	}
	
	@Override
	public String getMessage() {
		return String.format("validated, but schema in %s has neither '@id' nor 'id' attribute",jsonSchemaSource);
	}
}
