# syntax = docker/dockerfile:1.2
FROM python:3.12-bookworm
EXPOSE 5000

ENV JAGEOCODER_DB2_DIR /opt/db2

WORKDIR /app

# Install the required Python packages.
# Note: CMake is needed for building pycapnp package.
COPY ./requirements.txt /tmp/
# RUN apt-get update && apt-get install -y make cmake gcc g++ libssl-dev
RUN apt-get update && apt-get upgrade -y
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install -r /tmp/requirements.txt

# Setup and run server
COPY ./server /app/server
COPY entrypoint.sh /tmp

# Run server
WORKDIR /app/server
ENTRYPOINT ["/bin/sh", "/tmp/entrypoint.sh"]

