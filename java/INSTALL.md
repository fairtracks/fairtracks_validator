# FAIRification Genomic Data Tracks JSON Schema validation install instructions, Java edition

In order to have a compiled version of the program you need to have a Java8 JDK installed.
Then, you only have to run from the command-line the program `mvwn`:

```bash
./mvnw clean scm:bootstrap package appassembler:assemble
```

Once done, the program directory is available at `target/appassembler`, having the executable wrappers at `target/appassembler/bin`.
