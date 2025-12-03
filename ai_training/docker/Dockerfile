FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-devel

RUN apt-get update -y && apt-get install -y libgl1-mesa-glx libglib2.0-0

WORKDIR /app
COPY ./requirements.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

WORKDIR /workdir
