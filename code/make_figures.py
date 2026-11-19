"""Figures. Reads out/ba_quality_table.csv and out/ba_year.csv; writes paper/fig_rates.pdf and
paper/fig_effects.pdf. Run from the repository root: python -I code/make_figures.py"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Times-like text and mathematics (STIX, shipped with matplotlib) to match the IEEE body text
plt.rcParams.update({"font.size": 8, "font.family": "serif", "font.serif": ["STIXGeneral"], "mathtext.fontset": "stix",
                     "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.labelsize": 8, "legend.fontsize": 7,
                     "axes.linewidth": 0.6, "axes.edgecolor": "#555555",
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
ax.minorticks_off()
lab = ["0", "0.001", "0.01", "0.1", "1", "10", "100"]
ax.set_xticklabels(lab), ax.set_yticklabels(lab)
ax.set_xlabel("Reported demand: anomalous hours (%)")
ax.set_ylabel("Forecast: anomalous hours (%)")
ax.grid(color=GRID, lw=0.5, zorder=0)
for b in ("SEC", "SWPP", "CHPD", "SPA", "PSEI", "WACM"):
    if b in T.index:
        x, y = max(T.loc[b, "demand_shared"], FLOOR) * 100, max(T.loc[b, "forecast_shared"], FLOOR) * 100
        ax.annotate(b, (x, y), xytext=(4, 2), textcoords="offset points", fontsize=7, color=INK)
ax.text(1.5e-3, 8, "forecast worse", fontsize=7, color="#666666")
ax.text(1.2, 1.6e-4, "demand worse", fontsize=7, color="#666666", ha="center")
ax.legend(loc="lower right", fontsize=7, handletextpad=0.2, borderaxespad=0.2, bbox_to_anchor=(1.0, 0.08))
fig.tight_layout(pad=0.3)
fig.savefig("paper/fig_rates.pdf")

# Fig 2: effects on MAPE and on the annual peak (share of BA-years above x, log x axis)
fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.95), sharey=True)
v = Y["rel_change"].dropna().values * 100
r = (Y["peak_rep"] / Y["peak_adj"]).replace([np.inf, -np.inf], np.nan).dropna().values
p = np.abs(r - 1) * 100
for ax, x, thr, lo, ticks, tl, xl in (
        (axs[0], v, 10, 1e-2, [1e-2, 1, 1e2, 1e4], ["0.01", "1", "100", "$10^4$"], "MAPE change, $x$ (%)"),
        (axs[1], p, 1, 1e-1, [1e-1, 1e1, 1e3, 1e5, 1e7], ["0.1", "10", "$10^3$", "$10^5$", "$10^7$"], "Peak difference, $x$ (%)")):
    g = np.logspace(np.log10(lo), np.log10(x.max() * 1.5), 600)
    ax.plot(g, [100 * (x > t).mean() for t in g], color="#0072B2", lw=1.4, drawstyle="steps-post")
    ax.axvline(thr, color="#888888", lw=0.8, ls="--")
    s_ = 100 * (x > thr).mean()
    ax.plot([thr], [s_], "o", ms=3.5, color="#D55E00", zorder=4)
    ax.annotate(f"{s_:.1f}%", (thr, s_), xytext=(4, 4), textcoords="offset points", fontsize=7.5, color="#D55E00")
    ax.set_xscale("log"), ax.set_xlim(lo, x.max() * 1.5), ax.set_ylim(0, 52)
    ax.set_xticks(ticks), ax.set_xticklabels(tl)
    ax.minorticks_off()
    ax.set_xlabel(xl)
    ax.grid(color=GRID, lw=0.5)
axs[0].set_ylabel("BA-years above $x$ (%)")
axs[0].set_title("(a) forecast MAPE", fontsize=8)
axs[1].set_title("(b) annual peak demand", fontsize=8)
fig.tight_layout(pad=0.3, w_pad=1.6)
fig.savefig("paper/fig_effects.pdf")

# Fig 3 (exploratory): monthly MAPE reduction from the best forecast shift, by BA
LM = pd.read_csv("out/lag_monthly.csv")
LM["t"] = pd.to_datetime((LM["ym"] // 100).astype(str) + "-" + (LM["ym"] % 100).astype(str) + "-15")
LM["gain"] = np.where(LM["best"] != 0, 100 * (1 - LM["mape_best"] / LM["mape0"]), 0.0)
bas = ["PJM", "CISO", "AZPS", "SC"]
COL = {-2: "#56B4E9", -1: "#0072B2", 1: "#D55E00"}
fig, axs = plt.subplots(len(bas), 1, figsize=(3.45, 2.75), sharex=True, sharey=True)
for ax, b in zip(axs, bas):
    x = LM[LM["ba"] == b]
    for k, c in COL.items():
        s = x[x["best"] == k]
        if len(s):
            ax.bar(s["t"], s["gain"], width=25, color=c, label={-2: "$k=-2$", -1: "$k=-1$", 1: "$k=+1$"}[k])
    ax.axhline(10, color="#888888", lw=0.6, ls="--")
    ax.set_ylim(0, 62)
    ax.set_yticks([0, 25, 50])
    ax.set_ylabel(b, rotation=0, fontsize=8, labelpad=15, va="center")
    ax.grid(axis="y", color=GRID, lw=0.4)
fig.supylabel("MAPE reduction from best shift (%)", fontsize=7.5, x=0.01)
h, l = [], []
for ax in axs:
    for hh, ll in zip(*ax.get_legend_handles_labels()):
        if ll not in l:
            h.append(hh), l.append(ll)
axs[0].legend(h, l, loc="upper right", fontsize=7, ncol=3, handlelength=1, columnspacing=0.8, borderaxespad=0.1)
fig.tight_layout(pad=0.3, h_pad=0.2)
fig.savefig("paper/fig_lag.pdf")
print("ok")
