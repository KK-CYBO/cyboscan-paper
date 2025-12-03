# Downstream analysis

This directory contains the analysis and figure-generation notebooks,
together with anonymized CSV files, used in:

> Nitta et al., *Clinical-grade autonomous cytopathology via whole-slide edge tomography*.

It is part of the **`cyboscan-paper`** repository.  
For a high-level system overview, release notes, and license information, please refer to the **repository root `README.md`** and `LICENSE`.

---

## Scope of this directory

This module focuses on **downstream analysis**:

- Statistical analyses of cell-level outputs
- Multicenter evaluation and summary statistics
- UMAP visualizations of cell embeddings
- Scanner and viewer latency measurements and plots
- Reproduction of the main quantitative figures and tables from the paper

All notebooks assume that upstream pipelines have already exported
anonymized CSV files with the schemas used here.

Typical subdirectories:

- `statistical_analysis/` – single-center pilot study analyses
- `multicenter_analysis/` – multicenter evaluation and related plots
- `umap_plot/` – UMAP notebooks for selected slides / cells
- `viewer_latency/` – viewer latency measurements and plots
- `scanner_latency/` – scanner latency measurements and plots
- `docker/` – Dockerfile and Python requirements for this analysis environment

---

## System Requirements

The notebook in this directory has been tested in the following environment:

- OS: Windows 11 (inside Docker container)
- Python: 3.12.7 (via Anaconda base image at /opt/conda/bin/python)
- Required packages (see `.docker/requirements.txt`):
  - `numpy<2`
  - `pandas`
  - `scikit-learn`
  - `matplotlib`
  - `seaborn`
  - `jupyterlab`

## Installation Guide

We recommend using the provided Docker environment to run the notebooks in this directory.

### 1. Build the Docker image

From the `downstream_analysis/` directory:

```bash
docker build -t cyboscan-downstream -f .docker/Dockerfile .
```
On a typical desktop machine with a stable internet connection, this step usually completes within a few minutes (depending mainly on Docker base image download speed).

This will:

Use mcr.microsoft.com/devcontainers/anaconda:1-3 as the base image

Install the Python packages listed in .docker/requirements.txt via pip


### 2. Launch JupyterLab inside a container

Still from downstream_analysis/:

```bash
docker run --rm -it \
  -p 8888:8888 \
  -v "$PWD":/app \
  cyboscan-downstream \
  jupyter lab --ip=0.0.0.0 --no-browser --NotebookApp.token='' --notebook-dir=/app
```

Then open the following URL in your browser:

http://localhost:8888

All notebooks under downstream_analysis/ will be available under /app
inside the container.

### 3. Run the notebooks

Once JupyterLab is running:

Navigate to the notebook of interest (for example
multicenter_analysis/0_check_data.ipynb).

Run all cells from top to bottom.

The generated figures and tables will be written to the same directory
as the notebook unless otherwise noted.


## Reproducing figures and tables

All main and Extended Data figures and tables in the paper can be
reproduced using the notebooks listed below and the datasets included
in this `downstream_analysis` directory.

All runtime estimates were measured inside the Docker environment described above on a typical desktop machine and are intended as rough guidelines rather than strict limits.

*Runtime estimates were measured inside the provided Docker container on a standard desktop; first runs may be slightly slower due to cache warm-up.*

### A. Single-center pilot study (**Fig. 4**, Extended Data Figure 6)
- **Notebook**: `statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb`  
- **Input**: `statistical_analysis/paper-figure_celllist.csv`  
- **Generates**: **Fig. 4** and **Extended Data Fig. 6**   
  - **Update in v1.1.0**: displays **q-values** for significance tests.
  - **Update in v1.1.1**: add **Cliff’s delta** effect sizes where applicable.
- **Expected runtime**: ~10 minutes

### B. Multicenter evaluation (**Fig. 5**, Extended Data Figs. 9–10)
All notebooks below assume the working directory is `multicenter_analysis/` and read a single CSV:
- `paper-figure_celllist_all.csv`.

- **Notebook**: `0_check_data.ipynb`  
  - **Supplementary Table 1**: Sample counts by center, HPV status, cytology category  
  - **Extended Data Fig. 9b**: Age distributions by center  
  - **Extended Data Fig. 10a**: Age distributions by preparation (SurePath / ThinPrep)
  - **Expected runtime**: <1 minute

- **Notebook**: `1_cytology-AI-plots.ipynb`  
  - **Extended Data Fig. 9a, 9c–d**: Whole-slide counts across centers (incl. *navicular*; abnormal-only)  
  - **Fig. 5a–b**: AI-detected LSIL/HSIL counts by diagnosis and center (violin + points)
  - **Expected runtime**: ~2–4 minutes

- **Notebook**: `2_cytology-AI-statistics.ipynb`  
  - **Supplementary Table 2**: Summary stats and within-center significance for AI-detected LSIL/HSIL counts (+ Cliff’s delta)
  - **Expected runtime**: <1 minute

- **Notebook**: `3_hpv.ipynb`  
  - **Fig. 5c–d**: LSIL/HSIL counts by HPV status (− / +), stratified by center (violin + boxplots) (+ Cliff’s delta)
  - **Expected runtime**: <1 minute

- **Notebook**: `4_roc-auc.ipynb`  
  - **Fig. 5e-f**: ROC for LSIL⁺ (LSIL, ASC-H, HSIL, SCC) and HSIL⁺ (HSIL, SCC), per center + all centers  
  - **Extended Data Fig. 10b–c**: ROC by sample preparation (SurePath / ThinPrep)  
  - **Extended Data Fig. 9e–f**: Threshold–AUC sensitivity curves for LSIL⁺ / HSIL⁺ (per center)
  - **Expected runtime**: ~15–25 minutes

- **Notebook**: `4_roc-auc2.ipynb`  
  - **Fig. 5e-f (overlay version)**: ROC for LSIL⁺ and HSIL⁺ with all centers
    overlaid in a single panel, for a more compact presentation  
  - **New in v2.0.0**: added in the revised analysis to reduce figure footprint while
    preserving per-center curves  
  - **Expected runtime**: ~5 minutes 

- **Notebook**: `5_roc-auc-hpv.ipynb`  
  - **Fig. 5g–h**: ROC for AI-based detection of **HPV positivity** with 95% CI; human operating points (ASC-US⁺, LSIL⁺) overlaid (h: all centers; i: Center C)
  - **Expected runtime**: ~1–2 minutes


### C. Viewer latency (**Extended Data Fig. 3b**)
- **Notebook**: `viewer_latency/viewer_latency.ipynb`  
- **Input**: `viewer_latency/viewer_latency_data/*.csv`  
- **Generates**: **Extended Data Fig. 3b** (latency vs. data size)
- **Expected runtime**: < 1 minute


### D. Scanner latency (**Extended Data Fig. 2h**)
- **Notebook**: `scanner_latency/scanner_latency.ipynb`  
- **Input**: `scanner_latency/*.csv`  
- **Generates**: **Extended Data Fig. 2h** (latency vs. image quality per subprocess)
  - **New in v2.0.0**: added boxplots with outliers for each image-quality / subprocess combination 
- **Expected runtime**: < 1 minute


### E. CMD-based cell population analysis (**Figure 3a-d**)
- **Notebook:** `umap_plot/plot_slide{1-4}.ipynb`  
  - `plot_slide1.ipynb` → Fig. 3a (NILM)  
  - `plot_slide2.ipynb` → Fig. 3b (NILM)  
  - `plot_slide3.ipynb` → Fig. 3c (LSIL)  
  - `plot_slide4.ipynb` → Fig. 3d (HSIL)  
- **Input:** `umap_plot/data/*.csv`  
- **Generates:** **Figure 3a-d** (CMD-based cell population analysis). Each panel contains three plots, from left to right:  
  1. scatter plot for gating out leukocytes and irrelevant objects  
  2. overlaid histogram of LSIL and HSIL probability scores  
  3. UMAP projection visualizing the remaining epithelial cells   
  - **Updated in v2.0.0**: added sample data to enable full reproduction, and
    changed the panel layout to use an overlaid LSIL/HSIL histogram (three plots
    per panel: dotplot – overlaid histogram – UMAP)  
- **Expected runtime**: ~1–3 minutes per notebook  


---

## Using this analysis with your own data

The notebooks in this directory can also be applied to custom datasets,
as long as your CSV files follow the same schemas as the example files
included in this repository.

Below we summarize which example CSV to use as a template for each
group of analyses.

### 1. Single-center pilot study (Fig. 4)

- **Template CSV**: `statistical_analysis/paper-figure_celllist.csv`
- **Used by**: `statistical_analysis/paper-figure_population-analysis_313-31y41.ipynb`
- **Typical use case**: applying the single-center population analysis
  (cell counts, distributions, significance tests) to a new cohort
  from a single site.

To reuse:

1. Inspect the columns in `paper-figure_celllist.csv` and prepare
   a CSV with the same column names and data types for your own dataset.
2. Update the input path in the notebook if needed.
3. Run all cells inside the Docker/JupyterLab environment.

### 2. Multicenter evaluation (Fig. 5, Extended Data Figs. 9–10)

- **Template CSV**: `multicenter_analysis/paper-figure_celllist_all.csv`
- **Used by**:
  - `multicenter_analysis/0_check_data.ipynb`
  - `multicenter_analysis/1_cytology-AI-plots.ipynb`
  - `multicenter_analysis/2_cytology-AI-statistics.ipynb`
  - `multicenter_analysis/3_hpv.ipynb`
  - `multicenter_analysis/4_roc-auc.ipynb`
  - `multicenter_analysis/4_roc-auc2.ipynb`
  - `multicenter_analysis/5_roc-auc-hpv.ipynb`

To reuse:

1. Use `paper-figure_celllist_all.csv` as a schema reference
   (e.g. center ID, diagnosis, HPV status, AI scores, etc.).
2. Create a new CSV with the same columns populated with your data.
3. Point the notebooks to your CSV (either by overwriting the file or
   editing the path in the first few cells).
4. Run the notebooks of interest; the figure mapping and runtime
   estimates are listed in the “Reproducing figures” section.

### 3. Viewer and scanner latency (Extended Data Figs. 2h, 3b)

- **Template CSVs**:
  - `viewer_latency/viewer_latency_data/*.csv`
  - `scanner_latency/*.csv`
- **Used by**:
  - `viewer_latency/viewer_latency.ipynb`
  - `scanner_latency/scanner_latency.ipynb`

To reuse:

1. Inspect the latency CSV files to understand the expected columns
   (e.g. data size, image quality, subprocess ID, latency in ms).
2. Export your own latency measurements into CSV files with compatible
   columns.
3. Update the input file paths in the notebooks if needed.
4. Run the notebooks to regenerate latency boxplots and summary figures.

### 4. CMD-based cell population analysis (Fig. 3a–d)

- **Template CSVs**: `umap_plot/data/*.csv`
- **Used by**:
  - `umap_plot/plot_slide1.ipynb` (Fig. 3a)
  - `umap_plot/plot_slide2.ipynb` (Fig. 3b)
  - `umap_plot/plot_slide3.ipynb` (Fig. 3c)
  - `umap_plot/plot_slide4.ipynb` (Fig. 3d)

Each CSV contains cell-level CMD features and AI probability scores
(LSIL / HSIL), together with metadata used to define the gates.

To reuse:

1. Use the CSVs under `umap_plot/data/` as schema examples.
2. Prepare CSV files for your own slides with the same column structure.
3. Update the input paths in `plot_slide{1–4}.ipynb` as needed, or
   duplicate one notebook per new slide.
4. Run the notebooks to generate dotplots, overlaid histograms, and
   UMAP panels for your dataset.


---

## Data availability (summary)

All tabular data required to reproduce the plots and numerical results
generated by the notebooks in this directory are provided as anonymized
CSV files.

- **Available**: cell-level CMD features and AI scores, slide- and center-level
  metadata, and latency measurements for the viewer and scanner experiments.
- **Not available**: raw cytology images, whole-slide scans, and per-cell
  image thumbnails derived from these scans.

As a consequence:

- All panels in **Figs. 3–5** and **Extended Data Figs. 2–10** that show dotplots, 
  histograms, UMAP projections, ROC curves, bar charts, violin plots, and latency summaries, 
  as well as the analyzed data underlying **Supplementary Tables 1-2** can be reproduced from 
  the provided CSV files.
- Operations that rely on the underlying image data — such as interactively
  gating regions in the UMAP space of Fig. 3 and displaying the corresponding
  cell images — cannot be reproduced with the public materials.

For details on data governance, ethics approvals, and how to request access
to image data under appropriate agreements, please refer to the Data
Availability statement in the main manuscript.

---
## License

The `downstream_analysis` directory is part of the `cyboscan-paper` repository,
which is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).  
© 2025 K.K.CYBO

Some portions of the code disclosed here may be covered by one or more patents.
The existence, scope, and jurisdiction of any such patents may vary, and
nothing in this repository grants any license to practice patented technology.

For details, please refer to the `LICENSE` file at the root of the repository.
