#!/bin/bash

REALPATH="$(realpath "$0")"
BASEDIR="$(dirname "$REALPATH")"
case "$BASEDIR" in
	/*)
		true
		;;
	*)
		BASEDIR="${PWD}/$BASEDIR"
		;;
esac

PYBASEDIR="${BASEDIR}/.pyRESTenv"
# Is there a prepared Python environment??
if [ ! -d "$PYBASEDIR" ] ; then
	python3 -m venv "$PYBASEDIR"
	source "$PYBASEDIR"/bin/activate
	pip install --upgrade pip
	pip install -r "${BASEDIR}"/requirements.txt -c "${BASEDIR}"/constraints.txt
fi

# Is there a configuration file?
pyfile="${BASEDIR}/$(basename "$0")".py
configfile="${pyfile}.yaml"
template_config="${configfile}.template"

if [ ! -f "$configfile" ] ; then
	# Try initializing it with the default values
	cp -dfT "${template_config}" "$configfile"
	if [ ! -f "$configfile" ] ; then
		echo "NO CONFIG FILE $configfile" 1>&2
		exit 1
	fi
fi

if [ -d "$PYBASEDIR" ] ; then
	source "${PYBASEDIR}/bin/activate"
	#exec pprofile -o /tmp/pprofile_$$.txt --exclude-syspath "${BASEDIR}/$(basename "$0")".py "$@"
	exec python3 "${BASEDIR}/$(basename "$0")".py "$@"
else
	echo "UNCONFIGURED" 1>&2
	exit 1
fi
