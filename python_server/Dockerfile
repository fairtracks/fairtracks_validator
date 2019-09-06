FROM python:3.6-slim
LABEL	maintainer="jose.m.fernandez@bsc.es" description="FAIRTracks JSON Schema validation server" src_uri="https://github.com/fairtracks/fairtracks_validator.git"

ARG	SERVERPATH=/server
ADD	*.txt fairtracks_validator.fcgi* "${SERVERPATH}"/
# Puny implementation
ADD	libs "${SERVERPATH}"/libs/
COPY	docker-build.sh /tmp

RUN	/tmp/docker-build.sh "$SERVERPATH"

# In this way is running as a standalone server on the port
EXPOSE	5000
CMD [ "/server/fairtracks_validator.fcgi", "standalone" ]
