"""Figures. Reads out/ba_quality_table.csv and out/ba_year.csv; writes paper/fig_rates.pdf and
paper/fig_effects.pdf. Run from the repository root: python -I code/make_figures.py"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.linewidth": 0.6, "axes.edgecolor": "#555555",
                     "xtick.color": "#333333", "ytick.color": "#333333", "axes.labelcolor": "#222222",
                     "legend.frameon": False, "pdf.fonttype": 42})
INK, GRID = "#222222", "#dddddd"
SIZE = {"small": ("#E69F00", "o", "< 500 MW"), "mid": ("#0072B2", "s", "500-5,000 MW"), "large": ("#009E73", "^", "> 5,000 MW")}
T = pd.read_csv("out/ba_quality_table.csv", index_col=0)
Y = pd.read_csv("out/ba_year.csv")
FLOOR = 1e-6

# Fig 1: per-BA anomaly rate, demand vs forecast (shared classes)
fig, ax = plt.subplots(figsize=(3.45, 2.9))
for k, (c, m, lab) in SIZE.items():
    s = T[T["size"] == k]
    ax.scatter(np.maximum(s["demand_shared"], FLOOR) * 100, np.maximum(s["forecast_shared"], FLOOR) * 100, s=22,
               marker=m, facecolor=c, edgecolor="white", linewidth=0.6, label=lab, zorder=3)
lim = [FLOOR * 100 * 0.6, 100]
ax.plot(lim, lim, color="#888888", lw=0.8, ls="--", zorder=1)
ax.set_xscale("log"), ax.set_yscale("log"), ax.set_xlim(lim), ax.set_ylim(lim)
ticks = [1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100]
ax.set_xticks(ticks), ax.set_yticks(ticks)
lab = ["0", "0.001", "0.01", "0.1", "1", "10", "100"]
ax.set_xticklabels(lab), ax.set_yticklabels(lab)
ax.set_xlabel("Reported demand: anomalous hours (%)")
ax.set_ylabel("Forecast: anomalous hours (%)")
ax.grid(color=GRID, lw=0.5, zorder=0)
for b in ("SEC", "SWPP", "CHPD", "SPA", "PSEI", "WACM"):
    if b in T.index:
        x, y = max(T.loc[b, "demand_shared"], FLOOR) * 100, max(T.loc[b, "forecast_shared"], FLOOR) * 100
        ax.annotate(b, (x, y), xytext=(4, 2), textcoords="offset points", fontsize=6.5, color=INK)
ax.text(1.5e-4, 6, "forecast worse", fontsize=6.5, color="#666666")
ax.text(1.2, 1.6e-4, "demand worse", fontsize=6.5, color="#666666", ha="center")
ax.legend(loc="lower right", fontsize=6.5, handletextpad=0.2, borderaxespad=0.2, bbox_to_anchor=(1.0, 0.08))
fig.tight_layout(pad=0.3)
fig.savefig("paper/fig_rates.pdf")

# Fig 2: effects on MAPE and on the annual peak (ECDF over BA-years)
fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.75), sharey=True)
v = Y["rel_change"].dropna().values * 100
r = (Y["peak_rep"] / Y["peak_adj"]).replace([np.inf, -np.inf], np.nan).dropna().values
for ax, x, thr, xl in ((axs[0], np.maximum(v, 1e-3), 10, "|MAPE change| (%)"),
                       (axs[1], np.maximum(np.abs(r - 1) * 100, 1e-3), 1, "|Peak change| (%)")):
    xs = np.sort(x)
    ax.step(xs, 1 - np.arange(1, len(xs) + 1) / len(xs), where="post", color="#0072B2", lw=1.6)
    ax.axvline(thr, color="#888888", lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_xlabel(xl)
    ax.grid(color=GRID, lw=0.5)
    ax.set_xlim(1e-3, x.max() * 2)
    tk = [1e-3, 1e-1, 1e1, 1e3, 1e5][: 4 if x.max() < 1e5 else 5]
    ax.set_xticks(tk)
    ax.set_xticklabels(["0", "0.1", "10", "$10^3$", "$10^5$"][: len(tk)])
axs[0].set_ylabel("Share of BA-years above")
axs[0].set_title("(a) forecast MAPE", fontsize=7.5)
axs[1].set_title("(b) annual peak demand", fontsize=7.5)
fig.tight_layout(pad=0.3)
fig.savefig("paper/fig_effects.pdf")
print("ok")
