# Last One Standing

**1,203 of 2,044** molecules have exactly one supplier in Canada today. That count is
already published by the regulator. The gradient that looks like a finding is mostly
arithmetic. Here is what is left.**

## Three claims, in descending order of how much we can defend

**1. The count is not ours.** PMPRB / Gaudette et al., *JAMA Health Forum* 2024 report **52 %**
of off-patent drugs in Canada in a monopoly market in 2022, with a thirteen-year series.
Zhang et al., *CMAJ Open* 2020 reaches ≈51 % from the same public database. We do not headline
58.9 %.

**2. The gradient is mostly arithmetic, and we print the null that shows it.**
Molecules with more suppliers disappear less often. But a molecule only leaves the market when
**every** supplier leaves, so if companies depart independently at rate *p*, the disappearance
rate falls as *p^k* with no signal at all. Measuring *p* from the cohort itself (0.486 in 2016):

| suppliers in 2016 | molecules | observed gone | arithmetic null p^k | difference |
|---|---:|---:|---:|---:|
| 1 | 1,233 | 37.8 % | 48.6 % | **-10.8 pp** |
| 2 | 279 | 27.2 % | 23.6 % | **+3.7 pp** |
| 3 | 175 | 11.4 % | 11.4 % | **-0.0 pp** |
| 4 | 106 | 5.7 % | 5.6 % | **+0.1 pp** |
| 5 | 84 | 9.5 % | 2.7 % | **+6.8 pp** |
| 6+ | 295 | 3.4 % | 1.3 % | **+2.1 pp** |

8 cells sit above that null and 6 below — **not one direction.** The
single-supplier cell is consistently *better* than the null, which is the opposite of the
story the raw gradient tells. So "supplier count predicts disappearance" is not a finding we
claim. `src/null.py` is the script that took it away from us.

**3. What is left is the thinning itself, which is a count and not a prediction.**
**407** of them once had two or more companies and now have one — reconstructed from every product Health Canada has ever authorised, not
inferred. That is measured market exit, and no null removes it.

## Today

| | |
|---|---:|
| molecules currently marketed (active-ingredient sets) | **2,044** |
| molecules with exactly one supplier | 1,203 (58.9 %) |
| of those, once had two or more | **407** (33.8 %) |
| single-supplier molecules with an unexpired listed patent | 343 |
| single-supplier molecules ever on the Patent Register at all | 513 |
| prescription-only, no unexpired patent, first marketed before 2006, one supplier | **382** |
| molecules once marketed in Canada and no longer | 6,651 |

## Does anything beat counting?

A logistic regression in **pure Python — no numpy, no scikit-learn** — fit on the 2006 cohort
and tested on 2011 and 2016. Features are restricted to what was knowable in the cohort year.

| cohort | molecules | gone | supplier count alone | model | difference |
|---|---:|---:|---:|---:|---:|
| 2011 | 2,120 | 748 | 0.690 | 0.754 | **+0.064** |
| 2016 | 2,172 | 586 | 0.681 | 0.758 | **+0.078** |

That is better by **+0.071 AUC**. Two honest limits on that number:

- **The label is the same endpoint for every cohort** — "is this molecule marketed today". The
  cohorts share it and overlap heavily in membership, so this is *three views of one endpoint*,
  not three independent replications.
- One feature, `rx`, is today's prescription status because the database carries no
  point-in-time value. `src/check.py` fails if any other feature starts reading the future,
  and `src/sabotage.py` re-introduces the leak to prove that check can fail.

| feature | weight |
|---|---:|
| `holders` | -0.908 |
| `lost_already` | +0.813 |
| `age_years` | +0.164 |
| `products_by_then` | -0.670 |
| `rx` | -1.376 |

`lost_already` — companies a molecule has *already* shed — outweighs how many it has now.

## What this does not claim

- **One supplier does not mean you will run out.** PMPRB's own shortage study (2022) found
  that of 8,558 shortage reports, only 2 % were single-source non-patented drugs, and
  single-source drugs were in shortage **22 %** of the time versus **32 %** for multi-source.
  Santhireswaran et al. (*JAMA Netw Open*, 2026) found drugs with more than 25 products
  available had the *higher* shortage intensity. If this page implied a supply warning it
  would be contradicted by the regulator. It does not.
- **"No unexpired patent" is not "off patent."** Only a minority of marketed DINs ever appear
  on the Patent Register at all; biologics and pre-1993 drugs often never listed one. The
  page says "no listed patent" everywhere, never "off patent."
- **Disappearing is usually obsolescence, not crisis.** We do not check whether a same-class
  survivor exists.
- **`company_name` is the market authorisation holder, not the plant.** Subsidiaries count as
  separate suppliers. Merging parents can only *raise* the single-supplier count, so
  **1,203 is the conservative direction** — a rare case where the unfixed weakness
  strengthens rather than threatens the claim.
- **Product lifespans are approximate.** Health Canada's status endpoint carries one row per
  product — the current status and the date it was set — not a history.

## Run it

```bash
python3 src/fetch_data.py     # ~50 MB, no key, no account
python3 src/build.py          # join -> data/molecules.json
python3 src/report.py         # every number quoted above
python3 src/export_web.py     # web/index.html, opens from the filesystem, no server
python3 src/check.py          # 26 checks, at a denominator that cannot shrink
python3 src/sabotage.py       # break 27 things on purpose; do the checks notice?
```

**A passing count is not a quality signal.** The first version of the check suite reported
15/15 while three deliberate defects walked straight through it:

| the defect | why it was missed |
|---|---|
| turn off date parsing entirely | the format check had *nothing to check* and passed on the empty set |
| stop recording `Last-Modified` when fetching | the cache meant nothing was re-fetched — the mutation changed no behaviour |
| skip injecting data into the page | the check never ran the generator, so it graded a stale `index.html` |

Only the first was a dead check. The second was a badly aimed defect and the third was a
missing one. `src/sabotage.py` prints those three outcomes — **caught / missed / invalid** —
separately, because "the check is dead" and "the mutation preserved behaviour" need different
fixes. After those repairs: **16 of 16 caught, denominator fixed at 16.**

## Sources

| | |
|---|---|
| Drug Product Database | `health-products.canada.ca/api/drug/{drugproduct,activeingredient,status,schedule,company}` |
| Patent Register | `https://pr-rdb.hc-sc.gc.ca/patent/Patent.zip` |

The Patent Register is a static file that updates on its own schedule. **`src/report.py` prints
its `Last-Modified` header**, because "fetched today" and "current as of today" are not the
same thing, and the difference is the patent cut-off date of this whole analysis.
