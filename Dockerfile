# syntax = docker/dockerfile:1.2
FROM python:3.9-alpine
EXPOSE 5000

ARG DICFILE=jukyo_all_v20.zip
ENV DICFILE /data/${DICFILE}
ENV JAGEOCODER_DB2_DIR /opt/db2

WORKDIR /app

# Install the required Python packages.
# CMake is needed for building pycapnp.
RUN apk add --no-cache linux-headers cmake make g++
COPY ./requirements.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install -r /tmp/requirements.txt

# Install address dictionary
# COPY ./data /data/
# RUN python3 -m jageocoder install-dictionary /data/${DICFILE}

# Build R-tree for reverse geocoding
# RUN python3 -m jageocoder reverse 140.0 35.0

# Setup server
COPY ./server /app/server

# Run server
WORKDIR /app/server
# ENV FLASK_APP=app FLASK_DEBUG=1
# CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
# CMD ["gunicorn", "app:app", "--bind=0.0.0.0:5000"]
COPY entrypoint.sh /tmp
ENTRYPOINT ["/bin/sh", "/tmp/entrypoint.sh"]
