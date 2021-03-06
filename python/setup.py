#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import re
import os
import sys

# In this way, we are sure we are getting
# the installer's version of the library
# not the system's one
sys.path.insert(0,os.path.dirname(__file__))

from fairtracks_validator import version as fairtracks_validator_version

# Populating the long description
with open("README.md", "r") as fh:
	long_description = fh.read()

# Populating the install requirements
with open('requirements.txt') as f:
	requirements = []
	egg = re.compile(r"#[^#]*egg=([^=&]+)")
	for line in f.read().splitlines():
		m = egg.search(line)
		requirements.append(line  if m is None  else m.group(1))


setuptools.setup(
	name="fairtracks_validator",
	version=fairtracks_validator_version,
	scripts=["fairGTrackJsonValidate.py"],
	author="José Mª Fernández",
	author_email="jose.m.fernandez@bsc.es",
	description="FAIRtracks JSON Validator",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/fairtracks/fairtracks_validator/tree/master/python",
	packages=setuptools.find_packages(),
	install_requires=requirements,
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
		"Operating System :: OS Independent",
	],
)
