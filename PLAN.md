# Analysis plan: recording errors in EIA-930 demand and forecast data, and their effect on evaluation

Status: fixed before any anomaly rate, forecast error or peak statistic was
computed for this study. Changes after this commit are logged as amendments at
the end, with the reason and what they change.

Target venue: IEEE PES ISGT Asia 2027 (full paper, IEEE format).

## What was looked at before this plan

- The EIA-930 six-month BALANCE files (July 2015 to the November 2026 vintage),
  downloaded for an earlier study (cp-forecast-value) with SHA-256 sums, and an
  extract of every BA (6,337,013 BA-hours, no duplicate timestamps, no
  unparseable numbers).
- Data availability only: the share of hours with a reported demand and a
  reported forecast per BA and year, and each BA's median demand.
- In the earlier study the author met individual errors in four BAs (for
  example a PJM demand value of about 2.1e9 MW and isolated spikes) and wrote
  the screening rule used below. This study measures such errors across all BAs.

## Question

How common are recording errors in the EIA-930 hourly demand and day-ahead
demand forecast series, how well do EIA's own adjusted demand values line up
with a simple screen, and how much do the errors change two things analysts
compute from these files: the accuracy of each BA's forecast and each BA's
annual peak?

Prior work screened and imputed the demand series (Ruggles et al., Scientific
Data 2020; the PUDL project) and EIA now publishes imputed and adjusted demand.
The forecast series has no published screen or imputation, and the effect of
errors on forecast evaluation and peak identification has not been measured.

## Data

- Columns: Demand Forecast (MW), Demand (MW), Demand (MW) (Imputed),
  Demand (MW) (Adjusted); local "Data Date" and hour; UTC end time.
- Window: local days 2016-01-01 to 2026-09-30.
- Sample: BAs whose demand and forecast are both present in at least 80% of
  hours in at least 8 of the 11 calendar years 2016 to 2026 (no size floor).
  Size groups for reporting: median demand below 500 MW, 500 to 5,000 MW, above
  5,000 MW.

## Anomaly classes (applied to reported demand and to the forecast separately)

Reference R_t: centred 168-hour rolling median of positive reported demand
(min 24 values) for the BA. Classes are assigned in this order, each hour at
most one class:

1. MISS: the cell is empty.
2. NONPOS: value <= 0.
3. OVER: value > 10 x R_t (gross errors, including overflow-like sentinels).
4. SPIKE: 2 x R_t < value <= 10 x R_t, or 0 < value < 0.3 x R_t.
5. FLAT: part of a run of at least 6 consecutive hours with exactly the same
   value (all hours of the run are counted), not already in classes 1 to 4.
6. COPY (forecast only): forecast exactly equal to reported demand for at
   least 24 consecutive hours (all hours of the run).
7. SHIFT (forecast only, per BA-month): the lag k in {-3, ..., 3} hours that
   minimises the mean absolute difference between forecast shifted by k and
   reported demand (over hours not in classes 1 to 6); the month is flagged if
   the best k is not 0 and its mean absolute difference is at least 20% below
   the value at k = 0. All hours of a flagged month count.

Anomaly rate of a series = hours in classes 2 to 7 / hours with a non-empty
value. The shared rate uses classes 2 to 5 only, so demand and forecast are
compared on the same classes.

## EIA's adjustments

An hour is EIA-changed if Demand (MW) (Adjusted) is present and differs from
reported demand by more than 0.5 MW, or reported demand is empty and the
adjusted value is present. Agreement with the screen: share of screened
demand anomalies (classes 2 to 5) that EIA changed, and share of EIA-changed
hours that the screen flags.

## Effects on what analysts compute

- Forecast accuracy: for each BA-year, MAPE of the forecast against reported
  demand (a) raw: every hour with both values present and reported demand > 0;
  (b) screened: hours in neither series' classes 2 to 7. Relative change
  |MAPE_raw / MAPE_screened - 1|. Ranking: Kendall tau between raw and screened
  MAPE across BAs within each year.
- Annual peak: for each BA-year, the maximum hourly demand from (a) reported
  values, (b) EIA adjusted values, (c) screened reported values. Share of
  BA-years where (a) and (b) differ by more than 1%, and where the peak date
  differs.

## Hypotheses

- **H1.** The shared anomaly rate is higher for the forecast than for reported
  demand in a majority of BAs. One-sided binomial sign test (ties dropped).
- **H2.** Raw and screened MAPE differ by more than 10% (relative) in at least
  10% of BA-years. Pre-specified descriptive threshold on the point share; the
  share is reported with a Clopper-Pearson interval, which treats BA-years as
  independent and is therefore optimistic.
- **H3.** The reported and EIA-adjusted annual peaks differ by more than 1% in
  at least 5% of BA-years. Same reporting as H2.
- **H4.** The shared anomaly rate of reported demand changed between 2016 to
  2019 and 2023 to 2026: two-sided sign test across BAs.

Holm over the two sign-test p-values (H1, H4) at family alpha 0.05.

## Pre-specified secondary analyses

1. Sensitivity of the class thresholds: SPIKE at (1.5, 0.5) and (3, 0.2);
   FLAT runs of at least 4 and at least 12 hours.
2. Anomaly rates by size group and by year.
3. Effect on peak-day forecast evaluation: share of BA-years whose top 5% days
   by reported daily maximum demand include at least one anomalous hour.
4. If the cleaned data of Ruggles et al. can be downloaded, agreement between
   their flags and this screen on overlapping hours (different EIA vintages;
   reported as descriptive).

## Outputs

out/results.json (every number in the paper comes from it through generated
LaTeX macros), out/ba_quality_table.csv (a per-BA quality scorecard), figures.

## What would change the conclusions

If anomalies are rare and change neither MAPE nor peaks, the paper says the
files can be used as published and the screen is unnecessary. If they are common
in the forecast but rare in demand, the recommendation is a forecast screen
before any evaluation. Either result is reported.

## Amendment 1 (18 November 2026, after the full results and an internal review)

Implementation fix (no result changed): the reference median, the run lengths and the SHIFT lags are computed on the complete hourly UTC grid. Before, rows missing from the files were dropped first.

Exploratory analyses added after the results, reported as exploratory:
- H2 with SHIFT months realigned by their best lag instead of removed. Six BA-years (CISO 2023, PJM 2020-2024) have every month flagged and so no pre-specified screened MAPE. Also reported: absolute changes in percentage points, and the median year-to-year change of screened MAPE as context for the 10% threshold.
- Peak-day exposure with days ranked by EIA-adjusted demand and the SHIFT class left out, because ranking by reported demand is partly circular.
- EIA agreement by class, with and without SEC; EIA value changes separated from EIA fills of empty cells; adjusted against screened annual peaks (the pre-specified comparison (c)).
- Monthly lag curves (code/lag_diag.py, out/lag_monthly.csv) to date the offsets and check for DST patterns.

Not carried out: the comparison with the cleaned data of Ruggles et al. (secondary analysis 4).
