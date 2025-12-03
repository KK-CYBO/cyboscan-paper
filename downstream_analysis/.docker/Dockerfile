FROM mcr.microsoft.com/devcontainers/anaconda:1-3

WORKDIR /app
COPY .docker/requirements.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt