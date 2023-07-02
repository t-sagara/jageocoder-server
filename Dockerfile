# syntax = docker/dockerfile:1.2
FROM python:3.9-alpine
EXPOSE 5000

WORKDIR /app

# RUN python3 -m pip install -U pip setuptools
RUN apk --no-cache add curl
RUN curl https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v20.zip \
    -o /tmp/jukyo_all_v20.zip
COPY ./requirements.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install -r /tmp/requirements.txt
RUN python3 -m jageocoder install-dictionary /tmp/jukyo_all_v20.zip

COPY ./server /app/server

WORKDIR /app/server
ENV FLASK_APP=app FLASK_DEBUG=1

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
