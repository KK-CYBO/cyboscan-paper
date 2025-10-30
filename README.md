# cyboscan-paper [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17465404.svg)](https://doi.org/10.5281/zenodo.17465404)
**Scope:** analysis & figure-generation code + anonymized CSVs. Excludes on-device image processing modules, AI training code/weights, and backend infrastructure (including the inference pipeline).

Companion repository for Nitta et al., *Clinical-grade autonomous cytopathology via whole-slide edge tomography*.

> **Releases & Versioning**
> - **v1.1.1** — Add Cliff’s delta (effect size) in selected statistics  
>   DOI: https://doi.org/10.5281/zenodo.17480516  
>   https://github.com/KK-CYBO/cyboscan-paper/releases/tag/v1.1.1
> - **v1.1.0** — Revision (multicenter analyses; Fig. 6e–f q-values)  
>   DOI: https://doi.org/10.5281/zenodo.17465404  
>   https://github.com/KK-CYBO/cyboscan-paper/releases/tag/v1.1.0
> - **v1.0.0** — Initial submission / medRxiv v1  
>   DOI: https://doi.org/10.5281/zenodo.17460808  
>   https://github.com/KK-CYBO/cyboscan-paper/releases/tag/v1.0.0

---

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

## Reproducible Figures

Below are the figures/tables that can be reproduced directly with public materials in this repository.  
All notebooks were validated inside the Docker environment.

### A. Single-center pilot study (original submission; **Fig. 6**)
- **Notebook:** `statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb`  
- **Input:** `statistical_analysis/paper-figure_celllist.csv`  
- **Generates:** **Fig. 6a–i**  
  - **Update in v1.1.0:** displays **q-values** on **Fig. 6e–f** (significance tests).
  - **Update in v1.1.1:** add **Cliff’s delta** effect sizes where applicable.

### B. Multicenter evaluation (revision; **Fig. 7**, Extended Data Figs. 7–8)
All notebooks below assume the working directory is `multicenter_analysis/` and read a single CSV, `paper-figure_celllist_all.csv`.

- `0_check_data.ipynb`  
  - **Supplementary Table 1**: Sample counts by center, HPV status, cytology category  
  - **Extended Data Fig. 7b**: Age distributions by center  
  - **Extended Data Fig. 8a**: Age distributions by preparation (SurePath / ThinPrep)

- `1_cytology-AI-plots.ipynb`  
  - **Extended Data Fig. 7a, 7c–d**: Whole-slide counts across centers (incl. *navicular*; abnormal-only)  
  - **Fig. 7a–b**: AI-detected LSIL/HSIL counts by diagnosis and center (violin + points)

- `2_cytology-AI-statistics.ipynb`  
  - **Supplementary Table 2**: Summary stats and within-center significance for AI-detected LSIL/HSIL counts (+ Cliff’s delta)

- `3_hpv.ipynb`  
  - **Fig. 7c–d**: LSIL/HSIL counts by HPV status (− / +), stratified by center (violin + boxplots) (+ Cliff’s delta)

- `4_roc-auc.ipynb`  
  - **Fig. 7e**: ROC for LSIL⁺ (LSIL, ASC-H, HSIL, SCC) and HSIL⁺ (HSIL, SCC), **per center + all centers**  
  - **Extended Data Fig. 8b–c**: ROC by sample preparation (SurePath / ThinPrep)  
  - **Fig. 7f–g**: Threshold–AUC sensitivity curves for LSIL⁺ / HSIL⁺ (per center)

- `5_roc-auc-hpv.ipynb`  
  - **Fig. 7h–i**: ROC for AI-based detection of **HPV positivity** with 95% CI; human operating points (ASC-US⁺, LSIL⁺) overlaid (h: all centers; i: Center C)

### C. Viewer latency (unchanged in revision; **Extended Data Fig. 3b**)
- **Notebook:** `viewer_latency/viewer_latency copy.ipynb`  
- **Input:** `viewer_latency/viewer_latency_data/*.csv`  
- **Generates:** **Extended Data Fig. 3b** (latency vs. data size)

> **Note:** Figure numbering reflects the revision manuscript and may be updated before camera-ready.

---

## Figures requiring proprietary data

The following still require non-public image datasets and are therefore **not fully reproducible** here:

- **Figure 5**
  - 5b (UMAP) & 5e,f (cell images): `umap_plot/Image_UMAP_313-31y41_154.ipynb`  
  - 5c (UMAP) & 5f (cells): `umap_plot/Image_UMAP_313-31y41_068.ipynb`  
  - 5d (UMAP) & 5g,h (cells): `umap_plot/Image_UMAP_313-31y41_119.ipynb`  
  These notebooks contain the code, but associated images are not included.

---

## Instructions for Use

To apply the analysis to your own dataset:
1. Prepare a CSV following the schemas used in:
   - `statistical_analysis/paper-figure_celllist.csv` (single-center)  
   - `multicenter_analysis/paper-figure_celllist_all.csv` (multicenter)
2. Adjust the input path in the chosen notebook as needed.
3. Execute all cells in Jupyter Lab (inside the Docker container).

---

## Data availability (summary)

Due to privacy and regulatory constraints, raw cytology image data are not publicly shared. 
We provide anonymized CSVs sufficient to reproduce the key quantitative figures in this repository. 
For details on data governance and access requests, please refer to the manuscript’s Data Availability statement.


## License

This repository is licensed under the MIT License.  
© 2025 K.K.CYBO

Please note that some portions of the code disclosed here may be covered by one or more patents. The presence, scope, and jurisdiction of such patents may vary, and this repository does not grant any license to use any patented technology.


For details, please refer to the `LICENSE` file included in this repository.
