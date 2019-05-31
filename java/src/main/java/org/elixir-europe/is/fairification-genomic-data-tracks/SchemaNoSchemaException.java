package org.elixir_europe.is.fairification_genomic_data_tracks;

public class SchemaNoSchemaException
	extends GenericSchemaException
{
	public SchemaNoSchemaException(String jsonSchemaSource) {
		super(jsonSchemaSource);
	}
	
	@Override
	public String getMessage() {
		return String.format("impossible to validate, as schema in %s has no $schema attribute",jsonSchemaSource);
	}
}
