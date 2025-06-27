FROM mcr.microsoft.com/devcontainers/anaconda:1-3

RUN apt-get update && apt-get install -y \ 
        libgl1

WORKDIR /app
COPY .docker/requirements.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt