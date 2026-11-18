"""Every number in the paper. Reads out/results.json, out/ba_quality_table.csv, out/ba_year.csv,
out/lag_diag.json; writes paper/macros.tex, paper/tab_classes.tex, paper/tab_lag.tex, out/macros.json.
Run from the repository root: python -I code/make_macros.py"""
import json

import numpy as np
import pandas as pd

R = json.load(open("out/results.json"))
T = pd.read_csv("out/ba_quality_table.csv", index_col=0)
Y = pd.read_csv("out/ba_year.csv")
L = json.load(open("out/lag_diag.json"))
H, S = R["hypotheses"], R["secondary"]
M = {}


def f(x, d=2):
    return f"{x:.{d}f}"


def pct(x, d=1):
    return f"{100 * x:.{d}f}"


def pvt(p):
    return "$<$0.001" if p < 0.001 else f"{p:.3f}" if p < 0.01 else f"{p:.2f}"


def pv(p):
    """Relation form for use as $p\res{key}$."""
    return "<0.001" if p < 0.001 else "=" + (f"{p:.3f}" if p < 0.01 else f"{p:.2f}")


M["nBa"], M["nHoursM"] = str(len(T)), f(T["hours"].sum() / 1e6, 2)
for k, v in T["size"].value_counts().items():
    M["nSize" + k.capitalize()] = str(v)
M["medDemShared"], M["medFcShared"] = pct(T["demand_shared"].median(), 3), pct(T["forecast_shared"].median(), 3)
M["medDemRate"], M["medFcRate"] = pct(T["demand_rate"].median(), 3), pct(T["forecast_rate"].median(), 3)
M["baAnyDem"], M["baAnyFc"] = str(int((T["demand_rate"] > 0).sum())), str(int((T["forecast_rate"] > 0).sum()))
for s, tag in (("demand", "Dem"), ("forecast", "Fc")):
    M[f"medMiss{tag}"] = pct(T[f"{s}_miss"].median(), 2)
    for c, n in S["bas_with_class"][s].items():
        M[f"ba{tag}{c.capitalize()}"] = str(n)
for sz in ("small", "mid", "large"):
    M[f"size{sz.capitalize()}Dem"] = pct(S["by_size"]["demand_shared"][sz], 3)
    M[f"size{sz.capitalize()}Fc"] = pct(S["by_size"]["forecast_shared"][sz], 3)
# H1, H4
h1, h4 = H["H1"], H["H4"]
M["hOnePos"], M["hOneN"], M["hOneP"], M["hOneHolm"] = str(h1["pos"]), str(h1["n"]), pv(h1["p"]), pv(h1["p_holm"])
M["hFourUp"], M["hFourN"], M["hFourDown"] = str(h4["pos"]), str(h4["n"]), str(h4["n"] - h4["pos"])
M["hFourP"], M["hFourHolm"] = pv(h4["p"]), pv(h4["p_holm"])
# H2
h2 = H["H2"]
M["hTwoK"], M["hTwoN"], M["hTwoShare"], M["hTwoLo"], M["hTwoHi"] = (str(h2["k"]), str(h2["n"]), pct(h2["share"]),
                                                                    pct(h2["lo"]), pct(h2["hi"]))
v = Y.dropna(subset=["rel_change"])
M["hTwoFifty"], M["hTwoHundred"] = str(int((v["rel_change"] > 0.5).sum())), str(int((v["rel_change"] > 1).sum()))
M["hTwoBas"] = str(v.loc[v["rel_change"] > 0.1, "ba"].nunique())
M["hTwoBasOf"] = str(v["ba"].nunique())
for sz in ("small", "mid", "large"):
    vv = v[v["size"] == sz]
    M["hTwoShare" + sz.capitalize()] = pct((vv["rel_change"] > 0.1).mean(), 0)
top = v.sort_values("rel_change", ascending=False).iloc[0]
M["worstMapeBa"], M["worstMapeYear"] = top["ba"], str(int(top["year"]))
M["worstMapeRaw"], M["worstMapeScr"] = f(top["mape_raw"], 0), f(top["mape_scr"], 1)
tau = S["kendall_by_year"]
M["tauMin"], M["tauMax"] = f(min(tau.values())), f(max(tau.values()))
M["tauMinYear"] = min(tau, key=tau.get)
# H3
h3 = H["H3"]
M["hThreeK"], M["hThreeN"], M["hThreeShare"], M["hThreeLo"], M["hThreeHi"] = (str(h3["k"]), str(h3["n"]), pct(h3["share"]),
                                                                              pct(h3["lo"]), pct(h3["hi"]))
M["hThreeDateK"], M["hThreeDateShare"] = str(h3["date_differs"]["k"]), pct(h3["date_differs"]["share"])
y = Y.dropna(subset=["peak_rel_diff"])
big = y[y["peak_rel_diff"] > 0.01]
M["hThreeRepHigher"] = str(int((big["peak_rep"] > big["peak_adj"]).sum()))
M["hThreeMedRatio"] = f(float((big["peak_rep"] / big["peak_adj"]).median()), 1)
M["hThreeBas"] = str(big["ba"].nunique())
for sz in ("small", "mid", "large"):
    yy = y[y["size"] == sz]
    M["hThreeShare" + sz.capitalize()] = pct((yy["peak_rel_diff"] > 0.01).mean(), 0)
yy = y.assign(r=(y["peak_scr"] / y["peak_adj"] - 1).abs())
M["scrVsAdjK"] = str(int((yy["r"] > 0.01).sum()))
pj = y[(y["ba"] == "PJM") & (y["peak_rep"] > 1e9)]
M["pjmSentinelYear"] = str(int(pj["year"].iloc[0])) if len(pj) else "--"
M["pjmSentinelGw"] = f(pj["peak_rep"].iloc[0] / 1e9, 2) if len(pj) else "--"
M["pjmTrueGw"] = f(pj["peak_adj"].iloc[0] / 1e3, 1) if len(pj) else "--"
# top days, EIA
td = S["top_days_contaminated"]
M["topK"], M["topN"], M["topShare"], M["topLo"], M["topHi"] = str(td["k"]), str(td["n"]), pct(td["share"]), pct(td["lo"]), pct(td["hi"])
E = S["eia"]
M["eiaMedChanged"], M["eiaScreenIn"], M["eiaInScreen"] = pct(E["median_changed"], 2), pct(E["pooled_screen_in_eia"], 0), pct(E["pooled_eia_in_screen"], 0)
M["eiaMaxBa"], M["eiaMax"] = T["eia_changed"].idxmax(), pct(T["eia_changed"].max(), 1)
# sensitivity of H1
V = S["variants"]
M["varPmin"], M["varPmax"] = pv(min(x["p"] for x in V.values())), pv(max(x["p"] for x in V.values()))
# highest forecast rates
fr = T.sort_values("forecast_rate", ascending=False)
for i, tag in enumerate(("One", "Two", "Three")):
    M[f"fcTop{tag}Ba"], M[f"fcTop{tag}Rate"] = fr.index[i], pct(fr["forecast_rate"].iloc[i], 0)
M["pjmShiftShare"] = pct(T.loc["PJM", "forecast_SHIFT"], 0)
M["chpdSpikeShare"] = pct(T.loc["CHPD", "forecast_SPIKE"], 0)
# lag diagnostic
off = {b: sorted(int(yr) for yr, q in r.items() if q["best"] != 0 and q["mape_best"] <= 0.9 * q["mape0"]) for b, r in L.items()}
off = {b: v for b, v in off.items() if v}
M["nOffsetBa"] = str(len(off))
pjm = [L["PJM"][str(yr)] for yr in off.get("PJM", [])]
M["pjmOffFirst"], M["pjmOffLast"] = str(min(off["PJM"])), str(max(off["PJM"]))
M["pjmMapeZero"] = f(np.mean([q["mape0"] for q in pjm]), 1)
M["pjmMapeBest"] = f(np.mean([q["mape_best"] for q in pjm]), 1)
M["pjmMapePre"] = f(np.mean([L["PJM"][str(yr)]["mape0"] for yr in (2016, 2017, 2018)]), 1)
M["pjmBestLag"] = str(pjm[0]["best"]).replace("-", "$-$")
rows = []
for b, yrs in sorted(off.items()):
    q = [L[b][str(yr)] for yr in yrs]
    lags = sorted({x["best"] for x in q})
    span = f"{yrs[0]}" if len(yrs) == 1 else (f"{yrs[0]}--{yrs[-1]}" if yrs == list(range(yrs[0], yrs[-1] + 1)) else ", ".join(map(str, yrs)))
    rows.append(f"{b} & {span} & {', '.join(str(k).replace('-', '$-$') for k in lags)} & "
                f"{np.mean([x['mape0'] for x in q]):.1f} & {np.mean([x['mape_best'] for x in q]):.1f} \\\\")
open("paper/tab_lag.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
# class table
CL = ["NONPOS", "OVER", "SPIKE", "FLAT", "COPY", "SHIFT"]
rows = []
for c in CL:
    cells = []
    for s in ("demand", "forecast"):
        if c in ("COPY", "SHIFT") and s == "demand":
            cells += ["--", "--"]
            continue
        col = T[f"{s}_{c}"]
        n = int((col > 0).sum())
        cells += [str(n), (f"{100 * col.max():.2f} ({col.idxmax()})" if n else "0")]
    rows.append(f"{c} & " + " & ".join(cells) + " \\\\")
open("paper/tab_classes.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")

with open("paper/macros.tex", "w", encoding="utf-8") as fh:
    fh.write("% generated by code/make_macros.py -- do not edit\n\\makeatletter\n")
    for k, v in sorted(M.items()):
        fh.write(f"\\expandafter\\def\\csname res@{k}\\endcsname{{{v}}}\n")
    fh.write("\\makeatother\n\\newcommand{\\res}[1]{\\ifcsname res@#1\\endcsname\\csname res@#1\\endcsname\\else\\textbf{??#1??}\\fi}\n")
json.dump(M, open("out/macros.json", "w"), indent=0)
print(len(M), "macros")
print({k: M[k] for k in ("pjmMapeZero", "pjmMapeBest", "pjmMapePre", "hThreeMedRatio", "nOffsetBa", "fcTopOneBa", "pjmSentinelGw")})
