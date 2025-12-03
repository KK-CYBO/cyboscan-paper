# Changelog
All notable changes to this project will be documented in this file.
This project follows Keep a Changelog and uses Semantic Versioning.

---

## [v2.0.0] - 2025-12-04

### Summary
Major release turning the repository from an analysis-only snapshot into a full end-to-end system implementation.

### Added
- New top-level modules implementing the full pipeline:
  - `edge_computing/` – Jetson / C++ / CUDA edge acquisition and compression.
  - `backend_image_vending/` – HEVC slide streaming backend and viewer API.
  - `backend_inference/` – AI inference backend (YOLOX + MaxViT).
  - `ai_training/` – model training pipelines and Docker environments.
- New downstream analysis components:
  - `downstream_analysis/UMAP_plot/` and `downstream_analysis/Data/` to reproduce dotplots, histograms, and UMAP plots in Fig. 3a–d.
  - `downstream_analysis/scanner_latency/` for scanner performance evaluation.

### Changed
- `LICENSE`: changed the project license from MIT to **AGPL-3.0**.
- Restructured the repository so that the previous analysis-only code now lives under `downstream_analysis/`.
- Updated figure and panel references in notebooks / docs to match the final manuscript numbering.

### Fixed
- None.

---

## [v1.1.2] - 2025-11-2
### Added
- **Expected run time** estimates for each reproducible notebook in `README.md` (“Reproducible Figures” section).

### Changed
- `README.md`: added a one-line note clarifying that runtime estimates were measured inside the provided Docker container on a standard desktop.

### Fixed
- None.

---

## [v1.1.1] - 2025-10-30
### Added
- Effect size **Cliff’s delta** to statistical notebooks:
  - `statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb`
  - `multicenter_analysis/2_cytology-AI-statistics.ipynb`
  - `multicenter_analysis/3_hpv.ipynb`

### Changed
- README: update DOI badge/links; note Cliff’s delta in relevant sections.
- Repository renamed to **cyboscan-paper** (links updated).

### Fixed
- Minor text polish in docs (no breaking changes).

---

## [v1.1.0] - 2025-10-28
### Added
- **multicenter_analysis/** (flat layout) with notebooks and evaluation CSV:
  - `paper-figure_celllist_all.csv`
  - `0_check_data.ipynb` — Supplementary Table 1; Extended Data Fig. 7b (age by center); Extended Data Fig. 8a (age by prep).
  - `1_cytology-AI-plots.ipynb` — Extended Data Fig. 7a, 7c–d; Fig. 7a–b.
  - `2_cytology-AI-statistics.ipynb` — Supplementary Table 2.
  - `3_hpv.ipynb` — Fig. 7c–d (counts by HPV status).
  - `4_roc-auc.ipynb` — Fig. 7e (per-center + all-centers ROC); Extended Data Fig. 8b–c; Fig. 7f–g (threshold–AUC sensitivity).
  - `5_roc-auc-hpv.ipynb` — Fig. 7h–i (HPV positivity ROC; 95% CI; human operating points).
- Folder-local README for `multicenter_analysis/` (how to run, expected outputs).

### Changed
- `statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb`:
  - Minor revision to display **q-values** on Fig. 6e–f (significance tests).

### Deprecated
- None.

### Fixed
- Minor doc updates and paths in top-level README to reflect the new multicenter analyses.

---

## [v1.0.0] - 2025-07-09
### Added
- Initial public release corresponding to the **initial manuscript / medRxiv v1**.
- Dockerized, pinned environment; notebooks for Fig. 6a–i and Extended Data Fig. 3b.
