# Recording errors in EIA-930 hourly demand and forecast data

Code, analysis plan and results for the paper "Recording Errors in EIA-930 Hourly Demand and Forecast Data and Their Effect on Forecast Evaluation and Annual Peaks".

- `PLAN.md`: the analysis plan, committed before any anomaly rate was computed, with Amendment 1 (a grid fix and exploratory analyses added after the results) and Amendment 2 (exploratory checks after an independent review, logged before they were run).
- `code/download_eia930.sh`: downloads the EIA-930 six-month BALANCE files and writes SHA-256 hashes.
- `code/extract_all.py`: extracts every balancing authority into one parquet file.
- `code/quality.py`: error classes, EIA agreement, effects on MAPE and annual peaks (`--check` runs the pipeline check). Writes `out/results.json`, `out/ba_quality_table.csv` (a per-BA quality scorecard) and `out/ba_year.csv`.
- `code/lag_diag.py`: exploratory yearly and monthly timestamp-offset diagnostics (`out/lag_diag.json`, `out/lag_monthly.csv`).
- `code/pjm_official_check.py` (Amendment 2): PJM's official summer coincident-peak hours 2022-2026 (transcribed from PJM's "Summer YYYY Peaks and 5CPs" reports; URLs and SHA-256 in the script, files not redistributed) against the hour of the daily peak of EIA-930 demand and forecast (`out/pjm_official_check.json`).
- `code/robust.py` (Amendment 2): threshold grid for H1 and H2, H2 without SHIFT and in percentage points, BA-cluster bootstrap intervals, H1 confounding variants, extreme-event check (`out/amendment2.json`, `out/ba_year_a2.csv`).
- `code/make_macros.py`, `code/make_figures.py`: every number, table and figure in `paper/`.

Run order: download, extract, `quality.py`, `lag_diag.py`, `pjm_official_check.py`, `robust.py`, macros, figures, then `pdflatex`/`bibtex` in `paper/`.
Python 3.11 with pandas 2.2.3, numpy 1.26.4, scipy 1.14.1, pyarrow 17.0.0, matplotlib 3.9.2.
