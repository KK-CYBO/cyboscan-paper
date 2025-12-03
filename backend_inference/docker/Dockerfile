FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    git \
    unzip \
    make \
    cmake \
    build-essential \
    libopencv-dev \
    libgl1-mesa-dev \
    python3-dev \
    python3-setuptools \
    ffmpeg \
    libavutil-dev \
    libavcodec-dev \
    libavformat-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev

ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV PATH=/usr/local/cuda/bin:$PATH
ENV CUDAToolkit_ROOT=/usr/local/cuda

RUN apt-get update && apt-get install -y \
    libcublas-12-0 \
    libcublas-dev-12-0 \
    libcusparse-12-0 \
    libcusolver-12-0 \
    libcurand-12-0 \
    libnpp-12-0 \
    libnvjpeg-12-0 


RUN apt-get clean && rm -rf /tmp/* /var/tmp/* /var/lib/apt/lists/* && apt-get -y autoremove
ENV VIDEO_CODEC_SDK_VERSION="12.2.72"
ENV NVIDIA_DRIVER_CAPABILITIES=all
ADD Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}.zip .
RUN unzip ./Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}.zip \
    && cp ./Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/Interface/*.h /usr/local/cuda/targets/x86_64-linux/include \
    && cp ./Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/Lib/linux/stubs/x86_64/libnvidia-encode.so /usr/local/cuda/targets/x86_64-linux/lib \
    && cp ./Video_Codec_SDK_${VIDEO_CODEC_SDK_VERSION}/Lib/linux/stubs/x86_64/libnvcuvid.so /usr/local/cuda/targets/x86_64-linux/lib \
    && ldconfig

ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/opt/conda/lib:$LD_LIBRARY_PATH

RUN git clone --recursive https://github.com/dmlc/decord
RUN cd decord && mkdir build && cd build && cmake .. -DUSE_CUDA=ON -DCMAKE_BUILD_TYPE=Release && make -j2 && cd ../python && python3 setup.py install

RUN ln -s /usr/lib/x86_64-linux-gnu/libnvcuvid.so.1 /usr/lib/x86_64-linux-gnu/libnvcuvid.so
RUN ln -s /usr/lib/x86_64-linux-gnu/libnvidia-encode.so.1 /usr/lib/x86_64-linux-gnu/libnvidia-encode.so

RUN conda install -y libffi
RUN conda install -y -c conda-forge "libstdcxx-ng>=13.2" && conda clean -afy
ENV LD_PRELOAD=/opt/conda/lib/libffi.so.8

WORKDIR /app
COPY ./requirements.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

WORKDIR /workdir
