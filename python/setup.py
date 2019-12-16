#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import re

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
	version="0.8.0",
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
		"Programming Language :: Python :: 2",
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
		"Operating System :: OS Independent",
	],
)
