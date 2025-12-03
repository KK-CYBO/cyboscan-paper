# Downstream analysis :: Multicenter analysis

This folder contains notebooks and a single CSV used to generate **multicenter** figures and tables for the manuscript  (Fig. 5, Extended Data Figs. 9–10, Supplementary Tables 1–2).  

All notebooks read the same input file, `paper-figure_celllist_all.csv`.
They are intended to be run inside the `downstream_analysis` Docker
environment (see the parent `downstream_analysis/README.md`), with the
current working directory set to this folder.

> **Update (v1.1.1):** Added **Cliff’s delta** (effect size) to selected statistical outputs in `2_cytology-AI-statistics.ipynb` and `3_hpv.ipynb`.

> **New in v2.0.0**: added `4_roc-auc2.ipynb`, which generates overlaid ROC curves for LSIL⁺ / HSIL⁺ across centers for a more compact visualization.

> **Working directory:** run these notebooks with the current working directory set to this folder.

---

## Contents

- `paper-figure_celllist_all.csv` — multicenter evaluation dataset used by **all** notebooks
- `0_check_data.ipynb` — data checks, sample counts, and basic distributions
- `1_cytology-AI-plots.ipynb` — multicenter plots of AI-detected LSIL/HSIL counts
- `2_cytology-AI-statistics.ipynb` — summary statistics and within-center tests (incl. Cliff’s delta)
- `3_hpv.ipynb` — analyses stratified by HPV status (incl. Cliff’s delta)
- `4_roc-auc.ipynb` — ROC and threshold–AUC analyses per center and by preparation
- `4_roc-auc2.ipynb` — overlaid ROC curves for LSIL⁺ / HSIL⁺ (introduced in v2.0.0)
- `5_roc-auc-hpv.ipynb` — ROC analyses for HPV positivity with human operating points

---
## Quick start

1. Build and start the Docker environment for `downstream_analysis`
   (see `downstream_analysis/README.md`).
2. Launch JupyterLab inside the container.
3. In JupyterLab, open any notebook in this folder and run all cells.  
   All paths are **relative** and assume `paper-figure_celllist_all.csv`
   is present in this folder.

---

## Input data

**`paper-figure_celllist_all.csv`**

- Aggregated, per-slide evaluation dataset spanning multiple centers.
- Used across all notebooks to derive counts, statistics, and ROC analyses.
- The CSV is anonymized and does **not** include any PHI.
- The notebooks expect columns sufficient to compute:
  - center / facility identifiers
  - cytology diagnosis categories
  - HPV status (− / +)
  - AI-detected per-class cell counts (including the additional *navicular* cell category)

---

## Notebooks and expected outputs

> For a complete mapping between notebooks and figure panels, including
> expected runtimes, see `downstream_analysis/README.md`
> (“Reproducing figures and tables”).  
> Below is a concise summary for the multicenter analysis notebooks.

### `0_check_data.ipynb`
Exploratory checks of the evaluation dataset:
- **Supplementary Table 1**: Sample counts by center, HPV status, and cytology category.
- **Extended Data Fig. 9b**: Age distributions per center.
- **Extended Data Fig. 10a**: Age distributions by preparation (SurePath vs ThinPrep).

### `1_cytology-AI-plots.ipynb`
Whole-slide cell count visualizations:
- **Extended Data Fig. 9c,d**: Distributions of whole-slide counts from 1,124 slides across four centers; (c) all annotated cell types incl. *navicular*; (d) abnormal/positive classes only.
- **Extended Data Fig. 9a**: Log-scaled absolute counts of six epithelial cell types (four centers).
- **Fig. 5a,b**: AI-detected LSIL (a) and HSIL (b) cell counts across centers (C, T, K, J), stratified by cytology diagnosis. Violin plots with per-slide points.

### `2_cytology-AI-statistics.ipynb`
Summary statistics and within-center significance testing:
- **Supplementary Table 2**: Statistics for AI-detected LSIL and HSIL counts (per center) (+ Cliff’s delta).

### `3_hpv.ipynb`
Counts by HPV status:
- **Fig. 5c,d**: AI-detected LSIL (c) and HSIL (d) cell counts by HPV status (−, +) within each center (C, T, K, J) (+ Cliff’s delta).  
  Violin plots with overlaid boxplots.

### `4_roc-auc.ipynb`
Slide-level diagnostic performance:
- **Fig. 5e-f**: ROC curves for detecting **LSIL⁺** (LSIL, ASC-H, HSIL, SCC) and **HSIL⁺** (HSIL, SCC) computed **per center**; includes an **All centers** ROC.
- **Extended Data Fig. 10b,c**: ROC by preparation type — SurePath (b) and ThinPrep (c).
- **Fig. 9e-f**: Threshold–AUC sensitivity curves for LSIL⁺ (f) and HSIL⁺ (g), per center.

### `4_roc-auc2.ipynb`  
- **Fig. 5e-f (overlay version)**: ROC for LSIL⁺ and HSIL⁺ with all centers
    overlaid in a single panel, for a more compact presentation  
  - **New in v2.0.0**: added in the revised analysis to reduce figure footprint while
    preserving per-center curves  

### `5_roc-auc-hpv.ipynb`
HPV positivity detection:
- **Fig. 5g-h**: Slide-level ROC for AI-based detection of **HPV positivity** with 95% confidence bands; human cytology operating points (ASC-US⁺, LSIL⁺) overlaid.  
  (h) All centers; (i) Center C only.

---

## Reproducibility notes

- All notebooks were executed and validated within the repository’s Docker image (see root `README.md`).
- Randomness is not expected to affect the reported aggregate metrics; if randomness is introduced, please set explicit seeds (`numpy.random.seed`, `random_state`) and keep BLAS threads fixed for stability.
- Plots are rendered inline; exporting to files is optional and controlled by cells within each notebook.

---

## License


This `multicenter_analysis` directory is part of the `cyboscan-paper` repository,
which is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).  
© 2025 K.K.CYBO

Some analyses may relate to patented technology; the repository **does not** grant any patent license. See the top-level `LICENSE` and README for details.
