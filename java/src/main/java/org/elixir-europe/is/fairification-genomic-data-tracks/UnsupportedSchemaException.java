package org.elixir_europe.is.fairification_genomic_data_tracks;

public class UnsupportedSchemaException
	extends GenericSchemaException
{
	protected String schemaId;
	public UnsupportedSchemaException(String jsonSchemaSource,String schemaId) {
		super(jsonSchemaSource);
		this.schemaId = schemaId;
	}
	
	@Override
	public String getMessage() {
		return String.format("validation of schema in %s is unsupported (%s)",jsonSchemaSource,schemaId);
	}
}
