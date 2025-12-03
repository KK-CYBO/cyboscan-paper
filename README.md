# cyboscan-paper [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17460807.svg)](https://doi.org/10.5281/zenodo.17460807)

Code accompanying the manuscript  
**“Clinical-grade autonomous cytopathology via whole-slide edge tomography”** (Nitta et al.)

This repository contains the research code implementing the full pipeline used in
the manuscript, from **edge-device acquisition and compression** through
**AI training**, **backend inference**, and **downstream statistical analyses**.

From version **2.0.0** onward, this repository is released under the
**AGPL-3.0 license** and is primarily intended to satisfy journal
code-availability requirements and to document the full system architecture.

---

## End-to-end workflow

The pipeline described in the paper can be viewed as a five-stage workflow.
Each stage corresponds to one top-level directory in this repository.

### 1. Edge acquisition & compression – `edge_computing/`

- Runs on an embedded device (e.g. NVIDIA Jetson Xavier NX).  
- Acquires 3D whole-slide edge tomography data.  
- Performs on-device reconstruction and **hardware-accelerated HEVC compression**.  
- Writes multi-layer slide files and related metadata to local storage.

**Output of this stage**

- HEVC-encoded slide videos (multi-layer edge tomography)  
- Acquisition metadata (exposure, focus steps, etc., depending on setup)

> For build instructions and hardware/SDK requirements, see  
> `edge_computing/README.md`.

---

### 2. Interactive slide viewing – `backend_image_vending/`

- Runs on a GPU server or workstation.  
- Opens the HEVC slide files produced in step 1.  
- Provides HTTP APIs to retrieve tiled images on demand.  
- Powers a web-based viewer for interactive inspection of compressed slides.

**Input**

- HEVC-encoded slides from `edge_computing/`

**Output**

- Network-accessible tile/volume streaming endpoints for human viewing.

> For API details, deployment examples, and viewer integration, see  
> `backend_image_vending/README.md`.

---

### 3. Model development & training – `ai_training/`

- Runs offline on GPU servers using non-public training datasets derived
  from the acquired slides.  
- Implements the training pipelines for cell classification (e.g. MaxViT-based models).  
- Supports cross-validation, ablations, and model selection reported in the
  manuscript.  
- Exports ONNX model files for deployment.

**Input**

- Curated training datasets constructed from the edge-acquired slides  
  (not distributed in this repository)

**Output**

- ONNX model file(s) for cell classification.

> For experiment configuration, Docker environments, and training scripts, see  
> `ai_training/README.md`.

---

### 4. Backend AI inference – `backend_inference/`

- Consumes:
  - HEVC slide files from **step 1**, and  
  - ONNX models from **step 3**.  
- Uses CUDA-accelerated video decoding (NVDEC) to read multi-layer slides.  
- Runs batched YOLOX inference to detect nuclei across the Z-stack.  
- Groups detections, selects the best-focused ROI per cell, and crops
  MaxViT-sized patches.  
- Runs MaxViT inference on the cropped patches and writes **per-cell
  predictions** to CSV.

**Input**

- HEVC slide files (from `edge_computing/`)  
- ONNX models from `ai_training` (for cell classification) and/or other compatible training pipelines
- Configuration in `inference.py` (paths, GPU settings, thresholds)

**Output**

- `celllist.csv` files containing, for each ROI:
  - slide index, spot index, cell index  
  - bounding box and focal plane (`z, x1, y1, x2, y2`)  
  - class scores / probabilities for the 10-class classifier used in the paper

> For container build instructions and example inference settings, see  
> `backend_inference/README.md`.

---

### 5. Downstream analysis & figures – `downstream_analysis/`

- Consumes the per-cell prediction CSVs from `backend_inference/`.  
- Combines them with study metadata and labels (where shareable) to reproduce:
  - multicenter evaluation,  
  - ROC/AUC curves and operating points,  
  - HPV-stratified and subgroup analyses,  
  - and other statistical results in the manuscript.  
- Provides Jupyter notebooks and scripts that regenerate the main and extended
  figures/tables (subject to data availability).

**Input**

- Inference CSVs from `backend_inference/`  
- Evaluation datasets and metadata (some not publicly distributable)

**Output**

- Analysis notebooks, plots, and tables corresponding to the paper’s results.

> For environment setup and notebook execution order, see  
> `downstream_analysis/README.md`.

---

## Repository layout

High-level directory structure:

```text
cyboscan-paper/
├── README.md              # This file
├── LICENSE                # AGPL-3.0 (from v2.0.0)
├── CHANGELOG.md
├── CITATION.cff
│
├── edge_computing/        # Jetson / C++ / CUDA-based edge-side software
│   ├── README.md          # Module description and build information
│   ├── src/               # Source code files
│   └── include/           # Source header files
│
├── ai_training/           # GPU server–side training code (primarily Python)
│   ├── README.md
│   ├── docker/
│   └── ...
│
├── backend_image_vending/ # Backend for streaming compressed 3D slides to viewers
│   ├── README.md          # Backend description and build information
│   ├── run.py             # Backend running script
│   ├── docker/            # Docker image environment files
│   └── api/               # Source code files
│
├── backend_inference/     # Backend AI inference services
│   ├── README.md
│   ├── docker/
│   └── ...
│
└── downstream_analysis/   # Notebooks and scripts for analyses, figures, and tables
    ├── README.md
    ├── .docker/
    └── ...
```

---

## Versioning and license

From **v2.0.0** onward:

- The repository is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.  
- All custom code necessary to reproduce the results in the manuscript is included here, subject to:
  - External vendor SDKs or drivers that must be obtained separately.
  - Data that cannot be redistributed for privacy or institutional reasons.
  - Third-party components that remain under their respective licenses.

Earlier releases (the **1.x** series):

- Contain only the downstream analysis and figure-generation code.  
- Are archived separately (with their own Zenodo DOIs) and remain available under their original license.  
- Represent analysis-only snapshots prior to the release of the full codebase.

Please see `CHANGELOG.md` and the GitHub **Releases** page for details about each version and associated Zenodo records.

---

## How to cite

If you use this code or build upon this work, please cite:

- The manuscript:  
  > *Clinical-grade autonomous cytopathology via whole-slide edge tomography*  
  > (Nitta et al., [update with final journal details before camera-ready])

- Optionally, a specific archived release of this repository via its Zenodo DOI, as referenced in the manuscript’s Code availability statement.

A machine-readable citation is provided in `CITATION.cff` and can be converted to other formats using tools such as `cffconvert`.
