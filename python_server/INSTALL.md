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

File `fairtracks_validator.fcgi.py.yaml` must contain the list of JSON Schemas to be validated by this server. The template file `[fairtracks_validator.fcgi.py.yaml](fairtracks_validator.fcgi.py.yaml)` can be used as the starting point. If there is no file when this server is run once, the template file is tried to be copied to the configuration one.

The format of the configuration file is simple, as only  two keys are acknowledged by the validation server:

* _`schemas`_, which is a list of JSON Schema URLs to be fetched.

* _`cacheDir`_, which is a directory where the schemas are cached.

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
