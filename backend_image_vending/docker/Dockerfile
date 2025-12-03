FROM nvcr.io/nvidia/cuda:11.8.0-devel-ubuntu22.04@sha256:94fd755736cb58979173d491504f0b573247b1745250249415b07fefc738e41f AS build

ENV NVIDIA_DRIVER_CAPABILITIES=all
ENV NVIDIA_VISIBLE_DEVICES=all
ENV CUDA_CACHE_DISABLE=0
ENV CUDA_CACHE_MAXSIZE=2147483648
ENV TORCH_CUDA_ARCH_LIST="6.0;6.1;7.0;7.5;8.0;8.6"
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
ENV CUDA_LAUNCH_BLOCKING=0
ENV PYTORCH_NVFUSER_DISABLE_FALLBACK=1
ENV TORCH_CUDNN_V8_API_ENABLED=1

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    libturbojpeg0-dev \
    ffmpeg \
    libavutil-dev \
    libavcodec-dev \
    libavformat-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    unzip \
    git \
    cmake \
    make

RUN apt-get clean && rm -rf /tmp/* /var/tmp/* /var/lib/apt/lists/* && apt-get -y autoremove

RUN pip install --upgrade pip

ENV VIDEO_CODEC_SDK_VERSION="11.0.10"
ADD docker/Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}.zip .
RUN unzip /Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}.zip \
    && cp /Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/cuviddec.h /usr/local/cuda/targets/x86_64-linux/include \
    && cp /Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/nvcuvid.h /usr/local/cuda/targets/x86_64-linux/include \
    && cp /Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/libnvidia-encode.so /usr/local/cuda/targets/x86_64-linux/lib \
    && cp /Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/libnvcuvid.so /usr/local/cuda/targets/x86_64-linux/lib \
    && cp /Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/libnvcuvid.so.1 /usr/local/cuda/targets/x86_64-linux/lib \
    && ldconfig

RUN pip install numpy==2.2.6

RUN git clone --recursive https://github.com/dmlc/decord
RUN cd decord && mkdir build && cd build && cmake .. -DUSE_CUDA=ON -DCMAKE_BUILD_TYPE=Release && make -j2 && cd ../python && python3 setup.py install
RUN rm /usr/local/cuda/targets/x86_64-linux/lib/libnvidia-encode.so \
    && rm /usr/local/cuda/targets/x86_64-linux/lib/libnvcuvid.so.1 \
    && rm /usr/local/cuda/targets/x86_64-linux/lib/libnvcuvid.so

WORKDIR /app

COPY docker/requirements.txt /tmp/

RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

ENV FLASK_APP=run.py
ENV FLASK_DEBUG=1
ENV PYTHONUNBUFFERED=1
ENV DECORD_EOF_RETRY_MAX=819200

RUN mkdir -p /var/log/gunicorn/

COPY . /app

CMD ["python3", "run.py"]
