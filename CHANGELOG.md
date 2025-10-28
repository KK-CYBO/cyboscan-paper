# Changelog
All notable changes to this project will be documented in this file.
This project follows Keep a Changelog and uses Semantic Versioning.

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

## [v1.0.0] - 2025-07-09
### Added
- Initial public release corresponding to the **initial manuscript / medRxiv v1**.
- Dockerized, pinned environment; notebooks for Fig. 6a–i and Extended Data Fig. 3b.
