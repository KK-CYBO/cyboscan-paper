# AI training

This directory contains a minimal, publicly shareable subset of the AI training code used in:

> Nitta et al., *Clinical-grade autonomous cytopathology via whole-slide edge tomography*.

It is part of the **`cyboscan-paper`** repository.  
For a high-level system overview, release notes, and license information, please refer to the **repository root `README.md`** and `LICENSE`.

---

## Scope of this directory

This module focuses on the **core AI training pipeline**:

- Model definition for the cell-level classifier
- Data loading and augmentation routines
- Loss computation and optimization loop
- Configuration examples for training

The full production training pipeline cannot be published because it depends on proprietary data and infrastructure. However, the essential training logic is preserved so that the structure and behavior of the central pipeline can be examined and reused.

---

## Directory structure

```text
ai_training/
│
├── training.py                 # Main training entry point
├── training_monitor.py         # Utilities for logging, metrics, and monitoring
├── training_custom_functions.py# Custom loss functions, metrics, and helpers
├── model_control.py            # Model definition and checkpoint / weight handling
├── docker/
│   ├── Dockerfile              # Builds CUDA-enabled AI training environment
│   └── requirements.txt        # Python dependencies for the Docker image
├── dataset/                    # Sample LMDB dataset (see "Dataset" section)
│   ├── data.mdb
│   └── lock.mdb
└── README.md
```

---

## System Requirements

The example training code is intended to run inside the provided Docker image.

Tested environment (inside the container):

- Base image: `pytorch/pytorch:2.2.2-cuda12.1-cudnn8-devel`
- Python: as provided by the base image
- Required Python packages (see `dockerfile/requirements.txt`):
  - `numpy<2`
  - `pandas`
  - `scikit-learn`
  - `opencv-python`
  - `matplotlib`
  - `timm`
  - `albumentations`
  - `lmdb`
  - `onnx`

Recommended hardware:

- NVIDIA GPU compatible with CUDA 12.1 (compute capability SM 6.0–8.6)
- Recommended GPU: RTX 30-series or newer, or RTX A4000 or later, with ≥ 16 GB VRAM

Host software:

- NVIDIA driver version 530.30.02 or newer
- Docker with the NVIDIA container runtime enabled (`nvidia-container-toolkit`)

---

## Dataset

A small example dataset is provided under `dataset/` for demonstration and testing. Because this dataset is intentionally limited in size, any model trained on it will **not** be accurate and cannot reproduce the quantitative results reported in the paper.

For meaningful experiments, please prepare and curate your own dataset and update the dataset paths in the configuration or training scripts accordingly.

### Dataset format (LMDB schema)

Training and validation data are stored in a single LMDB environment.  
The provided data loader expects the following key–value structure:

- `classlist` – pickled list of class names (`List[str]`).  
  The integer class IDs used for labels correspond to indices in this list.

- `num-train` – total number of training images (integer).
- `num-val` – total number of validation images (integer).

- `img-t0`, `img-t1`, `img-t2`, ... – training image data.  
  Each key stores a single image (e.g., encoded as PNG or JPEG).  
  The suffix (`0`, `1`, `2`, ...) is a zero-based integer index.

- `class-t0`, `class-t1`, `class-t2`, ... – training labels.  
  Each key stores the integer class ID corresponding to `img-t*` with the same index.

- `meta-t0`, `meta-t1`, `meta-t2`, ... – optional metadata for training images.  
  Each value is a pickled Python object (typically a dict) with per-image metadata.

- `img-v0`, `img-v1`, `img-v2`, ... – validation image data (same format as `img-t*`).
- `class-v0`, `class-v1`, `class-v2`, ... – validation labels (same format as `class-t*`).
- `meta-v0`, `meta-v1`, `meta-v2`, ... – optional metadata for validation images (same format as `meta-t*`).

Each img-t* / img-v* value must be a JPEG- or PNG-encoded image byte stream that can be decoded by cv2.imdecode(..., cv2.IMREAD_COLOR).

As long as your LMDB dataset follows this schema, it can be used as a drop-in replacement for the sample dataset by pointing the training configuration to the corresponding LMDB path.

---

## Build and execution

### Docker image build instructions

To build and run the training environment, run the following in the `docker` directory:

```bash
cd docker
docker build -t cyboscan-ai-training -f Dockerfile .
```

### Running the training container

To run the training code, start a container with access to the repository and GPU.
From your host system, run:

```bash
docker run --gpus all \
  --ipc=host \
  -v /path/to/cyboscan-paper:/workdir \
  -it cyboscan-ai-training bash
```

Then, inside the container:

```bash
cd /workdir/AI_training
python training.py
```

Adjust /path/to/cyboscan-paper and the internal paths as needed to match your local directory layout.

The build time depends on hardware, network bandwidth, and Docker cache status.
The initial build may take longer than subsequent builds. 

## Output model and logs

By default, the trained model and training logs are written to the output/ directory under AI_training/.

The final model is stored in the Open Neural Network Exchange (.onnx) format.

Intermediate checkpoints and log files (e.g., loss / accuracy history) may also be stored in the same directory, depending on the training configuration.

Please refer to training.py and related configuration files for details on file naming and output paths.

## Runtime

The wall-clock training time depends primarily on:

- the number of training images (and classes),
- the number of epochs, and
- the available GPU hardware.

As a rough guideline:

- Training on the provided sample dataset (≈ 30 images per class) finishes within **a few minutes** on a recent NVIDIA GPU (e.g., RTX 30-series or later).
- In the experiments reported in the paper, training the model for up to 30 epochs on approximately 220k train and validation images took **around 30-40 hours** on a single NVIDIA RTX 6000 Ada.

Actual runtimes may differ depending on I/O performance, data augmentation settings, and other implementation details.

---
## License

The `ai_training` directory is part of the `cyboscan-paper` repository,
which is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).  
© 2025 K.K.CYBO

Some portions of the code disclosed here may be covered by one or more patents.
The existence, scope, and jurisdiction of any such patents may vary, and
nothing in this repository grants any license to practice patented technology.

For details, please refer to the `LICENSE` file at the root of the repository.
