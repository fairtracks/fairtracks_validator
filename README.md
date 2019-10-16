# FAIRification of Genomic Data Tracks JSON Schema validation

**NOTE:** _This repo was originally hosted at [FAIRification of Genomic Data Tracks Standards](//github.com/fairtracks/fairtracks_standard) repository, where the defined JSON Schemas are maintained_

The validation and consistency check tools are hosted in this directory. They were designed to work on complete sets of JSON files, spread over several directories.

These tools (currently, both [Python](python) and [Java](java)) implement next extensions:

* Unique values check: When the `unique` attribute is declared, the values assigned in that part of the schema on a set of JSON contents must be unique. The check includes all the loaded JSON contents. There are several examples inside [test-data](test-data). Its behaviour is the next:

  + If `unique` is a _`true`_ JSON value, the whole value in that position is used for the uniqueness check.
  
  + If `unique` is an array of strings, and the whole value is an object, those strings are the names of the keys whose values form the tuple to be validated.

* Format `curie`: This format represents a CURIE, whose namespace should be registered in [identifiers.org](https://identifiers.org/) (a copy of the registry is downloaded and cached). When this format is used, next attributes are used to manage its behavior:
  
  + `namespace`: It can be either a single string, or an array of them. Each one of these strings are the schemes allowed for the values. The schemes should be registered in [identifiers.org](https://identifiers.org/).
  
  + `matchType`: It is an optional, single enumerated value string. It rules the validation behavior. It can be:
    
      - `basic`: Only validates that the namespace of the value is in the list declared in `namespace` attribute.

      - `loose`: (default). It validates that the value (either having or not the scheme prefix) is valid against any of the patterns registered in [identifiers.org](https://identifiers.org/) for the schemes declared in `namespace` attribute.

      - `canonical`: The value must always have a correct scheme prefix, and the value to the right of the prefix must validate against the pattern registered on the namespace with the same scheme.

* Format `term`: This format represents an ontology term, which must be valid in one or more ontologies publicly reachable. When this format is used, next attributes are used to change its behavior:

  + `ontology`: (REQUIRED). This attribute can be either a single URI formatted string or an array of them. Each URI must resolve to a valid ontology, in OWL format. These ontologies are downloaded and cached, so the validation is locally done. It complains when any of the declared ontologies is unreachable.
  
  + `matchType`: It is an optional, single enumerated value string. It rules the validation behavior. It can be:
  
      - `exact`: (default). The value must be an exact IRI representing an ontological term defined in one of the ontologies declared in attribute `ontology`.
      
      - `suffix`: The value must be the suffix of at least one IRI representing an ontological term.
      
      - `label`: The value must be equal to at least one label assigned to an ontological term defined in one of the ontologies.
  
  + `ancestors`: This attribute can be either a single IRI or an array of them. The terms declared here must exist in at least one ontology, and the values to validate must have among its ancestors at least one of these terms.

You can use any of the reference implementations, [Python 2.x / 3.x](python) and [Java 8+](java), as any of them should do the same validations and consistency checks than the others.

There is also a [Python validation server](python_server), which uses [Python extendend validator](Python). You can find more documentation in that subdirectory.

You can find in [test-data](test-data) a JSON Schema using these formats, and also two sample JSONs, one with errors, and another one which validates against the schema.

## Original work

The code currently in this repository started as a fork from code currently available at [extended JSON Schema validators](//github.com/inab/extended-json-schema-validators) repository.
