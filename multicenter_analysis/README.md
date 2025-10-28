# Multicenter Analysis

This folder contains notebooks and a single CSV used to generate **multicenter** figures and tables for the manuscript revision.  
All notebooks read the same input file, `paper-figure_celllist_all.csv`, and were validated to run inside the Docker environment provided at the repository root (see the top-level `README.md`).

> **Working directory:** run these notebooks with the current working directory set to this folder.

---

## Contents

- `paper-figure_celllist_all.csv` — Evaluation dataset used by **all** notebooks in this folder.
- `0_check_data.ipynb`
- `1_cytology-AI-plots.ipynb`
- `2_cytology-AI-statistics.ipynb`
- `3_hpv.ipynb`
- `4_roc-auc.ipynb`
- `5_roc-auc-hpv.ipynb`

---

## Quick start

1. Build and start the Docker environment from the repository root (see root `README.md`).
2. Launch Jupyter Lab inside the container.
3. Open any notebook in this folder and run all cells.  
   All paths are **relative** and assume `paper-figure_celllist_all.csv` is present in this folder.

---

## Input data

**`paper-figure_celllist_all.csv`**

- Aggregated, per-slide evaluation dataset spanning multiple centers.
- Used across all notebooks to derive counts, statistics, and ROC analyses.
- The CSV is anonymized and does **not** include any PHI.
- The notebooks expect columns sufficient to compute:
  - center/facility identifiers,
  - cytology diagnosis categories,
  - HPV status (− / +),
  - AI-detected per-class cell counts (including the additional *navicular* cell category).


---

## Notebooks and expected outputs

### `0_check_data.ipynb`
Exploratory checks of the evaluation dataset:
- **Supplementary Table 1**: Sample counts by center, HPV status, and cytology category.
- **Extended Data Fig. 7b**: Age distributions per center.
- **Extended Data Fig. 8a**: Age distributions by preparation (SurePath vs ThinPrep).

### `1_cytology-AI-plots.ipynb`
Whole-slide cell count visualizations:
- **Extended Data Fig. 7c,d**: Distributions of whole-slide counts from 1,124 slides across four centers; (c) all annotated cell types incl. *navicular*; (d) abnormal/positive classes only.
- **Extended Data Fig. 7a**: Log-scaled absolute counts of six epithelial cell types (four centers).
- **Fig. 7a,b**: AI-detected LSIL (a) and HSIL (b) cell counts across centers (C, T, K, J), stratified by cytology diagnosis. Violin plots with per-slide points.

### `2_cytology-AI-statistics.ipynb`
Summary statistics and within-center significance testing:
- **Supplementary Table 2**: Statistics for AI-detected LSIL and HSIL counts (per center).

### `3_hpv.ipynb`
Counts by HPV status:
- **Fig. 7c,d**: AI-detected LSIL (c) and HSIL (d) cell counts by HPV status (−, +) within each center (C, T, K, J).  
  Violin plots with overlaid boxplots.

### `4_roc-auc.ipynb`
Slide-level diagnostic performance:
- **Fig. 7e**: ROC curves for detecting **LSIL⁺** (LSIL, ASC-H, HSIL, SCC) and **HSIL⁺** (HSIL, SCC) computed **per center**; includes an **All centers** ROC.
- **Extended Data Fig. 8b,c**: ROC by preparation type — SurePath (b) and ThinPrep (c).
- **Fig. 7f,g**: Threshold–AUC sensitivity curves for LSIL⁺ (f) and HSIL⁺ (g), per center.

### `5_roc-auc-hpv.ipynb`
HPV positivity detection:
- **Fig. 7h,i**: Slide-level ROC for AI-based detection of **HPV positivity** with 95% confidence bands; human cytology operating points (ASC-US⁺, LSIL⁺) overlaid.  
  (h) All centers; (i) Center C only.

---

## Reproducibility notes

- All notebooks were executed and validated within the repository’s Docker image (see root `README.md`).
- Randomness is not expected to affect the reported aggregate metrics; if randomness is introduced, please set explicit seeds (`numpy.random.seed`, `random_state`) and keep BLAS threads fixed for stability.
- Plots are rendered inline; exporting to files is optional and controlled by cells within each notebook.

---

## License

Code in this folder is covered by the repository’s license (MIT).  
Some analyses may relate to patented technology; the repository **does not** grant any patent license. See the top-level `LICENSE` and README for details.
