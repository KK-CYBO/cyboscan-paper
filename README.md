# cyboscan-manuscript
This repository contains the data analysis code used in the paper by Nitta et al., Clinical-grade autonomous cytopathology via whole-slide edge tomography.

## System Requirements

This repository has been tested in the following environment:

- OS: Windows 11 (inside Docker container)
- Python: 3.12.7 (via Anaconda base image at /opt/conda/bin/python)
- Required packages (see `.docker/requirements.txt`):
  - numpy 1.26.4
  - pandas 2.2.2
  - opencv-python 4.11.0.86
  - matplotlib 3.9.2
  - seaborn 0.13.2
  - scikit-learn 1.5.1
  - jupyter 1.0.0
  - jupyterlab 4.2.5
  - pillow 10.4.0
  - pillow-heif 0.22.0
  - loguru 0.7.3
  - markupsafe 2.0.1
- Additional system dependencies:
  - libgl1 (for OpenCV GUI functions)

## Installation Guide

We recommend using the provided Docker environment for reproducibility.

### 1. Prerequisites

- Docker installed on your system
- (Optional) VS Code with Remote - Containers extension, if using as a Dev Container

### 2. Build the Docker container

In the root of the repository, run the following command:

bash
docker build -t cyboscan-analysis -f .docker/Dockerfile .

Typical install time on a standard desktop:

Docker image build: ~3–5 minutes (depending on internet speed)

Container startup: <1 minute

## Demo

This section explains how to reproduce key figures from the paper using the provided code and data.

### 📊 Reproducible Figures

The following figure panels can be reproduced using the available notebooks and data in this repository.

#### 🔹 Figure 6 (Panels a–i)

To reproduce the entire Figure 6 (panels a through i), run the following notebook:

`statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb`

Required data:

`statistical_analysis/paper-figure_celllist.csv`

Simply launch Jupyter Lab inside the Docker container and open the notebook above. All plots will be generated upon execution. Sample outputs are viewable on GitHub via the rendered notebook.

**Expected run time:** ~10 minutes

#### 🔹 Extended Data Figure 3b (Latency vs. Data Size)

This figure can be reproduced by running:

`viewer_latency/viewer_latency copy.ipynb`

Required data:

`viewer_latency/viewer_latency_data/*.csv`

**Expected run time:** <1 minute

### ⚠️ Figures Requiring Proprietary Data

The following figures involve visualizations generated from data not included in this repository due to privacy or proprietary restrictions.

#### 🔸 Figure 5

- **Figure 5b (UMAP plot) & 5e,f (cell images):**  
  `umap_plot/Image_UMAP_313-31y41_154.ipynb`

- **Figure 5c (UMAP) & 5f (cells):**  
  `umap_plot/Image_UMAP_313-31y41_068.ipynb`

- **Figure 5d (UMAP) & 5g,h (cells):**  
  `umap_plot/Image_UMAP_313-31y41_119.ipynb`

These notebooks contain the necessary code, but the associated image data is not included in this repository. Therefore, executing these notebooks will not fully reproduce the figures unless the private datasets are available.

If needed, we can consider releasing a limited, anonymized subset of data to support reproducibility.

## Instructions for Use

This repository can also be used to analyze new datasets, provided that the data format matches the structure expected by the notebooks.

For example, the notebook `statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb` expects a CSV file containing per-cell measurements (e.g. morphometry, intensity, classification), similar to `paper-figure_celllist.csv`.

To apply the analysis to your own dataset:
1. Prepare a CSV file with a similar structure (see `statistical_analysis/paper-figure_celllist.csv` for reference).
2. Modify the file path in the notebook accordingly.
3. Run the notebook in Jupyter Lab to generate plots and statistics.

Currently, image-level analysis (e.g. UMAP projections in `umap_plot`) requires additional image datasets that are not included in this repository.

## Reproduction Instructions (Optional)

The following steps summarize how to reproduce the main quantitative results in the paper:

- **Figure 6a–i**: Run all cells in  
  `statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb`

- **Extended Data Figure 3b**: Run  
  `viewer_latency/viewer_latency copy.ipynb`

The data for these figures are included in the repository. All other figures that rely on image data (e.g. UMAP projections in Figure 5) require access to non-public datasets.

To reproduce those results, please contact the authors or request access to a subset of anonymized data (pending approval).

## License

This repository is licensed under the MIT License.  
© 2025 K.K.CYBO

Please note that some portions of the code disclosed here may be covered by one or more patents. The presence, scope, and jurisdiction of such patents may vary, and this repository does not grant any license to use any patented technology.

For details, please refer to the `LICENSE` file included in this repository.
