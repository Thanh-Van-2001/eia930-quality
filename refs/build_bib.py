"""Build refs.bib from Crossref BibTeX for DOIs (fails loudly if a DOI does not resolve)
and print each title for a by-eye check. Manual entries live in refs/manual.bib.
Run: python build_bib.py <out.bib>"""
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "ref-check/0.1 (academic reference verification)"}
DOIS = {
    "ruggles2020eia": "10.1038/s41597-020-0483-x",
    "chen2010cleansing": "10.1109/TSG.2010.2053052",
    "luo2018robustness": "10.1016/j.ijforecast.2017.08.004",
    "sobhani2020temperature": "10.1016/j.ijforecast.2019.04.022",
    "hyndman2006another": "10.1016/j.ijforecast.2006.03.001",
    "hong2016probabilistic": "10.1016/j.ijforecast.2015.11.011",
    "clopper1934use": "10.1093/biomet/26.4.404",
    "kendall1945ties": "10.1093/biomet/33.3.239",
    "dechalendar2021reconciliation": "10.1016/j.apenergy.2021.117761",
    "dechalendar2019tracking": "10.1073/pnas.1912950116",
    "yue2019descriptive": "10.1109/TSG.2019.2894334",
}
TITLE_FIX = {"US electricity": "{US} electricity", "THE USE OF CONFIDENCE OR FIDUCIAL LIMITS ILLUSTRATED IN THE CASE OF THE BINOMIAL": "The use of confidence or fiducial limits illustrated in the case of the binomial",
             "THE TREATMENT OF TIES IN RANKING PROBLEMS": "The treatment of ties in ranking problems"}


def get(url, tries=5):
    for t in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code != 429 or t == tries - 1:
                raise
            time.sleep(20 * (t + 1))
        except urllib.error.URLError:
            if t == tries - 1:
                raise
            time.sleep(5 * (t + 1))


out = []
for key, doi in DOIS.items():
    bib = get(f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex")
    bib = re.sub(r"^@(\w+)\{[^,]+,", lambda m: "@" + m.group(1) + "{" + key + ",", bib.strip(), count=1)
    bib = re.sub(r"\s*url=\{[^}]*\},", "", bib)
    bib = re.sub(r",\s*month=\w+", "", bib)
    bib = bib.replace("&amp;", r"\&")
    for a, b in TITLE_FIX.items():
        bib = bib.replace(a, b)
    t = re.search(r"title=\{(.*?)\},", bib)
    print(f"{key:26s} {t.group(1)[:95] if t else '??'}")
    out.append(bib)
    time.sleep(0.5)
manual = open(os.path.join(os.path.dirname(__file__), "manual.bib"), encoding="utf-8").read()
open(sys.argv[1], "w", encoding="utf-8").write("\n\n".join(out) + "\n\n" + manual)
print(len(out) + manual.count("\n@") + manual.startswith("@"), "entries written")
