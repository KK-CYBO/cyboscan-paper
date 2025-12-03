# Backend image vending

This directory contains a minimal, publicly shareable subset of the backend image vending code used in:

> Nitta et al., *Clinical-grade autonomous cytopathology via whole-slide edge tomography*.

It is part of the **`cyboscan-paper`** repository.  
For a high-level system overview, release notes, and license information, please refer to the **repository root `README.md`** and `LICENSE`.

The code in this directory captures the core logic of the backend responsible for
decoding tiled video data and producing cropped image regions used by the viewer.
Deployment-specific integration, authentication, and operational tooling are out of
scope, so that the essential image decoding and tiling pipeline can be examined,
tested, and adapted in other environments.

---

## Scope of this directory

This module focuses on the **image vending backend** that serves tiles and regions from very large microscopy images stored as compressed video:

- Decoding of tiled video files into image frames
- Extraction of arbitrary spatial regions (crops) from the decoded frames
- Support for multiple resolution levels and Z-stack layers
- A Deep Zoom Image (DZI)-style tiling scheme for viewer integration
- HTTP endpoints that expose metadata and individual tiles on demand

In the deployed system, the full-slide viewer interacts with this backend by
requesting metadata and DZI-structured tiles, each of which is decoded on demand
from the underlying video file. Authentication (e.g. via JWT) and per-user caching
are used in production to avoid reinitializing expensive decoders; in this sample,
these mechanisms are kept minimal to highlight the core image decoding and tiling logic.

---

## Directory structure

```text
backend_image_vending/
│
├── api/
│   ├── __init__.py              # API package initialization / app factory
│   └── tile/
│       ├── models.py            # Coordinate mapping and image extraction logic
│       ├── routes.py            # Flask routes that expose the tile API
│       ├── utils.py             # Shared utility functions
│       ├── video_decoder.py     # GPU-based video decoding (e.g., NVDEC via Video Codec SDK / Decord)
│       └── config.py            # Configuration for tile backend (paths, cache, etc.)
│
├── docker/
│   ├── Dockerfile               # Builds the CUDA-enabled backend image
│   └── requirements.txt         # Python dependencies for the backend
│
├── run.py                       # Application entry point for the backend server
└── README.md                    # This documentation
```

**Note**: The NVIDIA Video Codec SDK (e.g. Video_Codec_SDK_11.0.10.zip) is not included in this repository.
To enable hardware-accelerated decoding, please obtain the SDK separately and follow the instructions in docker/Dockerfile.

---

## System Requirements

The backend is intended to run inside the provided Docker image and relies on
GPU-accelerated video decoding (NVDEC) for high-throughput tile serving.

### Hardware requirements

- NVIDIA GPU compatible with CUDA 11.8 (compute capability SM 6.0–8.6)
- Recommended GPU: RTX 30-series or newer, or RTX A4000 or later, with ≥ 16 GB VRAM
- Host system with support for the NVIDIA Container Toolkit
- Recommended host: modern multi-core CPU and at least 16–32 GB system RAM

The application depends on CUDA kernels and hardware-accelerated NVDEC video
decoding, so newer GPUs with sufficient memory provide more stable processing
of large multi-layer microscopy video files.

### Host software

Before building or running the container, the following software must be installed
on the host:

- NVIDIA driver version 520.xx or newer
- Docker with the NVIDIA container runtime enabled (`nvidia-container-toolkit`)

### Additional files

The Docker build expects the NVIDIA Video Codec SDK archive to be present in the
repository:

- `docker/Video_Codec_SDK_11.0.10.zip`

This archive is **not** distributed with the repository.  
To enable hardware-accelerated decoding, download the corresponding Video Codec
SDK from NVIDIA under its license, place it at the above path, and then build
the Docker image.

The container image is based on `nvcr.io/nvidia/cuda:11.8.0-devel-ubuntu22.04`
and installs:

- Python 3.11
- FFmpeg and related `libav*` libraries
- TurboJPEG
- NVIDIA Video Codec SDK headers and libraries (from the provided ZIP)
- Decord (built from source with CUDA enabled)
- Python dependencies listed in `docker/requirements.txt`

These components are required for GPU-accelerated video decoding, tile extraction,
and the backend HTTP service.

---

## API Endpoints

The backend exposes a small set of HTTP endpoints for metadata and tile retrieval.

1. Metadata retrieval : /metadata/`<slidename>`

This endpoint returns structural information such as tile size, overlap, and the overall pixel dimensions of the slide.
Metadata is cached for performance, and clear error messages are returned if information is missing or invalid.

2. Tile Image Retrieval : /tile/`<slidename>`/z`<z>`/dzi`<level>`/y`<y>`-x`<x>`

This endpoint returns a decoded tile from the multi-resolution image pyramid.
The backend verifies the requested Z-layer, retrieves a processor instance, decodes the required frame from the video, crops the requested tile region, and encodes the result as JPEG using TurboJPEG.
Errors such as invalid coordinates, missing files, or decoding failures are caught and returned with detailed diagnostic information.

3. Releasing Video Resources : /unload/`<slidename>`

This endpoint frees cached decoders and associated GPU memory for a given user and slide.

## Coordinate Mapping & image extraction
This backend provides GPU-accelerated decoding of microscopy slide videos and extracts DeepZoom-compatible image tiles. A single GPU decoder is shared across users, and the correct tile region is computed from slide metadata and cropped directly on CUDA tensors for maximum performance.

### VideoManager handling
`VideoManager` handles hardware-accelerated video decoding, keeps frames resident in GPU memory, and provides fast random access by frame index. When first created, it asynchronously upgrades itself to GPU mode, allowing decoding and frame delivery without CPU–GPU transfer overhead.

### BaseImageProcessor
`BaseImageProcessor` calculates the correct frame number and spatial offsets for a tile request, crops the decoded GPU tensor, optionally resizes it according to the zoom level, and returns a final RGB tile. The processor also keeps track of per-slide video managers, releasing them automatically when no users remain.

## GPU video decoding
This module provides a streamlined GPU video decoding backend using Decord with NVIDIA CUDA.
The system is designed for high-throughput frame extraction, suitable for applications such as tile-based deep-zoom visualization.

### VideoManager
The `VideoManager` class manages a single GPU-based video decoder. When initialized with a video path, it extracts basic metadata using `ffprobe` and creates a Decord `VideoReader` that decodes frames directly into GPU tensors. Each requested frame is returned as a PyTorch tensor residing on the GPU, enabling fast downstream image transformations without CPU round-trips.
GPU decoding requires that CUDA support is available in the Docker environment and that Decord is built with GPU support enabled. This design eliminates CPU fallback logic and ensures consistent, predictable performance for high-resolution video decoding workloads.

---

## Backend architecture

The backend image retrieval pipeline is composed of three functional layers.  
Each layer has a clear responsibility, and requests flow through them in the following order:

```text
[1] routes.py  →  [2] models.py  ↔  [3] video_decoder.py
```

### 1. `routes.py` — endpoint and request-handling layer

* Receives API requests through Flask endpoints.
* Validates parameters such as slide name, zoom level, coordinates, and Z-index.
* Performs only lightweight processing and forwards requests to the image extraction layer.

### 2. `models.py` — Coordinate mapping and image extraction

* Computes the mapping from Deep Zoom–style tile coordinates to the original microscopy video space.
* Determines which video frame(s) contain the requested region.
* Crops the appropriate area from the decoded frame and prepares DZI-style tiles.
* Manages video decoding sessions (e.g., per user or per slide) for efficient reuse.

### 3. `video_decoder.py` — GPU video decoding layer

* Performs hardware-accelerated video decoding using NVIDIA Video Codec SDK + CUDA.
* Decodes only the necessary frame instead of loading entire videos into memory.
* Returns decoded frames to `models.py` which then performs cropping and tile generation.



---

## Build and execution

### Docker image build instructions
To build the backend system, place the required Video Codec SDK archive (Video_Codec_SDK_11.0.10.zip) into the same directory as the Dockerfile because the decoder relies on NVIDIA’s hardware-accelerated video libraries. Once the file is present, execute the following command from the backend directory:

```bash
docker build -f docker/Dockerfile -t image-backend .
```
This will construct a CUDA-enabled Docker image, compiling Decord with GPU support and installing all required dependencies.

### Running the backend

After the build finishes, run the backend:

```bash
docker run --gpus all -p 5000:5000 image-backend
```
The backend will start the Flask-based tile server and GPU video decoder.

### Build time
The build process compiles Decord from source with GPU support and installs CUDA-dependent libraries, so it is expected to take 4-15 minutes depending on hardware and internet bandwidth.
Actual build time may vary due to network speed or Docker cache status.

### Image acquisition time
The GPU-based decoding pipeline extracts frames directly from high-resolution video streams and converts them to image tiles with bilinear interpolation and margin-aware cropping. The exact image acquisition performance depends on:

* GPU model and memory bandwidth
* Number of concurrent user requests
* Deep-zoom level

Quantitative measurements of the image acquisition latency and throughput were obtained experimentally and are reported in the paper.


---
## License

The `backend_image_vending` directory is part of the `cyboscan-paper` repository,
which is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).  
© 2025 K.K.CYBO

Some portions of the code disclosed here may be covered by one or more patents.
The existence, scope, and jurisdiction of any such patents may vary, and
nothing in this repository grants any license to practice patented technology.

For details, please refer to the `LICENSE` file at the root of the repository.
