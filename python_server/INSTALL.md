# FAIRification Genomic Data Tracks JSON Schema validation server install instructions

The source code of this API is written for Python 3.5 or later. It depends on standard libreries, plus the ones declared in [requirements.txt](requirements.txt).

* In order to install the dependencies you need `pip` and `venv` Python modules.
	- In a Ubuntu clean installation, next packages are needed: `python3-venv`, `python3-dev`, `build-essential` and `git`.
	- `venv` is also available in many Linux distributions. In some of these distributions `venv` is integrated into the Python 3.5 (or later) installation.
	- `pip` is available in many Linux distributions (Ubuntu package `python-pip` or `python-pip-whl`, CentOS EPEL package `python-pip`), and also as [pip](https://pip.pypa.io/en/stable/) Python package.

* The creation of a virtual environment and installation of the dependencies in that environment is done running:

```bash
python3 -m venv .pyRESTenv
source .pyRESTenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt

# Next commands are to assure a static swagger ui interface is in place
SWAGGER_UI_VER=3.23.8
for dest in .pyRESTenv/lib/python3.*/site-packages/flask_restplus ; do
	if [ ! -d "$dest"/static ] ; then
		if [ ! -f swagger-ui-${SWAGGER_UI_VER}.tar.gz ] ; then
			wget --content-disposition https://github.com/swagger-api/swagger-ui/archive/v${SWAGGER_UI_VER}.tar.gz
		fi
		if [ ! -d swagger-ui-${SWAGGER_UI_VER} ] ; then
			tar xf swagger-ui-${SWAGGER_UI_VER}.tar.gz swagger-ui-${SWAGGER_UI_VER}/dist
		fi
		cp -pTr swagger-ui-${SWAGGER_UI_VER}/dist "$dest"/static
	fi
done
rm -rf swagger-ui-${SWAGGER_UI_VER}*
```

## Setup

File `fairtracks_validator.fcgi.py.yaml` must contain the list of JSON Schemas to be validated by this server. The template file `[fairtracks_validator.fcgi.py.yaml.template](fairtracks_validator.fcgi.py.yaml.template)` can be used as the starting point. If there is no file when this server is run once, the template file is tried to be copied to the configuration one.

### Configuration file format

The format of the configuration file is simple, as only  two keys are acknowledged by the validation server:

* _`host`_, when it is run in production, optional internet address where the server is listening to petitions.

* _`port`_, optional port where the server is run in either standalone or debug modes. Default is **5000**.

* _`max_file_size`_, optional size, in MB, of the maximum allowed transferred file size. Default is **16**.

* _`schemas`_, which is a list of JSON Schema URLs to be fetched.

* _`cacheDir`_, which is a directory where the schemas are cached.

## Debug testing

In order to test the server in debug mode, you only have to run it in the previously created environment:

```bash
./fairtracks_validator.fcgi debug
```

If you can read something like next, it is properly working, waiting for request at port 5000 (the default one):

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

## Standalone running

This server can be run in standalone mode,

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
	# This is needed to assure in a cold start of the server that
	# the ontologies have the chance to be fetched
	FcgidIOTimeout	240
	ScriptAlias / "/path/to/fairtracks_validator.fcgi/"

	<Location />
		# If uncommented, limit request body to 1GB
		#LimitRequestBody	1073741824
		# If uncommented, no limits on request body
		#LimitRequestBody	0
		
		SetHandler fcgid-script
		Options +ExecCGI
		Require all granted
	</Location>
```

## Docker integration

This repository contains a [Dockerfile](Dockerfile) which can be used to create a docker image of the server.

```bash
docker build -t fairtracks/validation_server .
```

Once the image is built, the image can tested issuing next command:

```bash
docker run -p 5000 --rm -ti fairtracks/validation_server
```

which publishes the server in the instance on the port 5000.

If you have your own customized configuration file, you can run the server with the next command:

```bash
docker run -p 5000 -v $PWD/myConfigFile.yaml:/server/fairtracks_validator.fcgi.py.yaml:ro --rm -ti fairtracks/validation_server
```
