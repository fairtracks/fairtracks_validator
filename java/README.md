# FAIRification Genomic Data Tracks JSON Schema validation, Java edition

The JSON schema should be compliant with JSON Schema Draft04, Draft06 or Draft07 specifications.

So, this validation program uses libraries compliant with that specification.

* This directory contains a Java project of a validator program, whose dependencies are defined in [pom.xml](pom.xml).
	- The dependencies are fetched, and the program is built running next command from this directory:
	  ```bash
	  ./mvnw package appassembler:assemble
	  ```
	
	- The generated bundle (the program, along all its dependencies), is available at `target/appassembler` subdirectory. It can be run using next command line:
	  ```bash
	  export PATH="${PWD}/target/appassembler/bin:$PATH"
	  fairGTrackJsonValidate ../../JSON-schemas/fair-gtrack.json {JSON file or directory+}
	  ```

The roots of this program come from [https://github.com/inab/benchmarking-data-model/tree/0.4.0/toolsForValidation](https://github.com/inab/benchmarking-data-model/tree/0.4.0/toolsForValidation)
