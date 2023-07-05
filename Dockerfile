# syntax = docker/dockerfile:1.2
FROM python:3.9-alpine
EXPOSE 5000

ENV JAGEOCODER_DB2_DIR /opt/db2

WORKDIR /app

# Install the required Python packages.
# Note: CMake is needed for building pycapnp package.
COPY ./requirements.txt /tmp/
RUN apk add --no-cache libstdc++-dev
RUN apk add --no-cache --virtual .pycapnp-builddeps linux-headers cmake make g++
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install -r /tmp/requirements.txt
RUN apk del .pycapnp-builddeps

# Setup and run server
COPY ./server /app/server
COPY entrypoint.sh /tmp

# Run server
WORKDIR /app/server
# ENV FLASK_APP=app FLASK_DEBUG=1
# CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
ENTRYPOINT ["/bin/sh", "/tmp/entrypoint.sh"]
