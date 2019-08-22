# FAIRification Genomic Data Tracks JSON Schema validation server install instructions

The source code of this API is written for Python 3.5 or later. It depends on standard libreries, plus the ones declared in [requirements.txt](requirements.txt).

* In order to install the dependencies you need `pip` and `venv` Python modules.
	- `pip` is available in many Linux distributions (Ubuntu package `python-pip`, CentOS EPEL package `python-pip`), and also as [pip](https://pip.pypa.io/en/stable/) Python package.
	- `venv` is also available in many Linux distributions (Ubuntu package `python3-venv`). In some of these distributions `venv` is integrated into the Python 3.5 (or later) installation.

* The creation of a virtual environment and installation of the dependencies in that environment is done running:

```bash
python3 -m venv .pyRESTenv
source .pyRESTenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt
# Next commands are to assure a static swagger ui interface is in place
if [ ! -d .pyRESTenv/lib/python3.5/site-packages/flask_restplus/static ] ; then
	wget --content-disposition https://github.com/swagger-api/swagger-ui/archive/v3.14.2.tar.gz
	tar xf swagger-ui-3.14.2.tar.gz swagger-ui-3.14.2/dist
	mv swagger-ui-3.14.2/dist .pyRESTenv/lib/python3*/site-packages/flask_restplus/static
	rm -r swagger-ui-3.14.2*
fi
```

## Setup

### Debug

File `validator_debug.py.yaml` must contain the list of JSON Schemas to be validated by this server. The template file `[fairtracks_validator.fcgi.py.yaml.template](fairtracks_validator.fcgi.py.yaml.template)` can be used as the starting point. For instance:

```bash
ln -s fairtracks_validator.fcgi.py.yaml.template validator_debug.py.yaml
```

### Production

File `fairtracks_validator.fcgi.py.yaml` must contain the list of JSON Schemas to be validated by this server. The template file `[fairtracks_validator.fcgi.py.yaml.template](fairtracks_validator.fcgi.py.yaml.template)` can be used as the starting point. If there is no file when this server is run once, the template file is tried to be copied to the configuration one.

### Configuration file format

The format of the configuration file is simple, as only  two keys are acknowledged by the validation server:

* _`schemas`_, which is a list of JSON Schema URLs to be fetched.

* _`cacheDir`_, which is a directory where the schemas are cached.

## Debug testing

In order to test the server in debug mode, you only have to run it in the previously created environment:

```bash
source .pyRESTenv/bin/activate
python validator_debug.py
```

If you can read something like next, it is properly working, waiting for request at port 5000:

```
* Owlready2 * Warning: optimized Cython parser module 'owlready2_optimized' is not available, defaulting to slower Python implementation
 * Serving Flask app "fairtracks_validator" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
* Owlready2 * Warning: optimized Cython parser module 'owlready2_optimized' is not available, defaulting to slower Python implementation
 * Debugger is active!
 * Debugger PIN: 294-971-606
```

If you open http://127.0.0.1:5000/ you will be able to browse and test the FAIR Tracks JSON Schema validator API using the embedded Swagger UI instance. The OpenAPI definition is available at the standard location, http://127.0.0.1:5000/swagger.json

## API integration into Apache

This API can be integrated into an Apache instance. The instance must have the module [FCGID](https://httpd.apache.org/mod_fcgid/) installed (package `libapache2-mod-fcgid` in Ubuntu).

```bash
sudo apt install apache2 libapache2-mod-fcgid
sudo a2enmod mod-fcgid
sudo service apache2 restart
sudo service apache2 enable
```

```apache
	FcgidMaxProcessesPerClass	5
	ScriptAlias / "/path/to/fairtracks_validator.fcgi/"

	<Location />
		SetHandler fcgid-script
		Options +ExecCGI
		Require all granted
	</Location>
```
