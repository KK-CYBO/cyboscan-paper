# Backend AI inference

This directory contains a minimal, publicly shareable subset of the backend AI inference code used in:

> Nitta et al., *Clinical-grade autonomous cytopathology via whole-slide edge tomography*.

It is part of the **`cyboscan-paper`** repository.  
For a high-level system overview, release notes, and license information, please refer to the **repository root `README.md`** and `LICENSE`.

This module implements the server-side AI inference pipeline that
- receives tiled image data from the image backend,
- runs nuclei detection and cell-level classification using models produced by the `ai_training` pipeline, and
- returns per-cell predictions and related metadata.

The example code preserves the essential processing logic (tile handling, batching, model loading, and post-processing), while omitting deployment-specific integration and infrastructure used in the production system.


---

## Directory structure

```text
backend_inference/
│
├── inference.py              : Inference entry point.
├── run_inference_full.py
├── cell_classify.py
├── findnuclei_yolox_batch.py
├── post_yolo_func.py
├── docker/
│   ├── Dockerfile            : Builds CUDA-enabled AI inference environment.
│   └── requirements.txt      : Python dependency list.
└── README.md
```

---

## System Requirements

To run this container, the system must meet several essential hardware conditions:

- NVIDIA GPU compatible with CUDA 12.1 (compute capability 6.0 or higher)
- GPU recommended: RTX 30-series or newer, or RTX A4000 or later, with 16 GB or more VRAM
- Host system must support the NVIDIA Container Toolkit

The application depends on CUDA kernels and hardware-accelerated NVDEC video decoding, so newer GPUs with higher memory capacity provide more stable processing of large multi-layer microscopy video files. Although older GPUs are technically supported, recent professional-grade GPUs ensure consistent performance and allow the decoder, image-processing pipeline, and AI inference to run without memory limitations.

A typical host environment benefits from modern CPUs and at least 16–32 GB of system RAM. These specifications support efficient decoding, caching, and image extraction without stalling the GPU pipeline.

Before building or running the container, the following software requirements must be satisfied:

- NVIDIA driver 530.30.02 or newer installed on the host
- Docker with NVIDIA container runtime enabled (`nvidia-container-toolkit`)
- `Video_Codec_SDK_12.2.72.zip` placed in the same directory as the Dockerfile (required for NVDEC header and library installation)

The container is based on the official PyTorch image with CUDA 12.1 and includes Python 3, FFmpeg, and the NVIDIA Video Codec SDK. These components are necessary for hardware-accelerated video decoding, tile extraction, and CUDA-backed image processing. The Decord library is built from source with CUDA enabled, which allows efficient frame access from video files.

---

## Build and execution


### Docker image build instructions

To build and run the training environment, run the following in the `docker` directory:

```bash
cd docker
docker build -t cyboscan-backend-inference -f Dockerfile .
```

### Running the inference

After the build finishes you can start inference by running (for example):

```bash
docker run --gpus all --rm -it \
  -v $(pwd)/..:/workdir \
  --name backend-inference \
  cyboscan-backend-inference \
  python inference.py
```

This command assumes you are running it from the backend_inference/docker directory, and mounts the project root into /workdir inside the container so that inference.py and related modules are visible.

## Inputs

The inference pipeline takes in three inputs.

1. The YOLOX model (specified by `yolo_model_path` in `inference.py`).
2. The MaxViT model (specified by `maxvit_model_path` in `inference.py`).
3. The input video path (specified by `input_video_path` in `inference.py`).

You can prepare the MaxViT model by following instructions in `ai_training`.
You can prepare the input video by referencing `edge_computing` and using custom hardware.

## Output Results

A `celllist.csv` file will be output in the `output` directory as inference is progressing. This can be used as an input of `downstream_analysis`. Rows in the output csv correspond to regions of interest (ROIs) with bounding box and R values for every class. The bounding box is described by 5 points [z, x1, y1, x2, y2] where z indicates the focal plane at which the ROI was found and (x1, y1) and (x2, y2) correspond to two opposing corners of the bounding box rectangle.

## Runtime and performance

### Build time
Building is expected to take 5-10 minutes depending on hardware and internet bandwidth.
Actual build time may vary due to network speed or Docker cache status.

### Inference time
Inference time depends strongly on the GPU model, its memory bandwidth, and
how well parameters such as batch size are tuned for that device.

As a reference, on a single NVIDIA RTX 6000 Ada GPU, processing a
40-layer × 10-spot image stack (yielding approximately 22,000 cells) with
the 10-class classifier used in the paper takes on the order of 100 seconds.

For other GPUs, you may need to adjust parameters such as the MaxViT batch
size and YOLO/MaxViT inference settings to balance throughput, memory usage,
and latency.

---
## License

The `backend_inference` directory is part of the `cyboscan-paper` repository,
which is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).  
© 2025 K.K.CYBO

Some portions of the code disclosed here may be covered by one or more patents.
The existence, scope, and jurisdiction of any such patents may vary, and
nothing in this repository grants any license to practice patented technology.

For details, please refer to the `LICENSE` file at the root of the repository.
