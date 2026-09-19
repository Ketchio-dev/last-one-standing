"""화면용 축약 데이터 + 템플릿 주입. grid-clock 과 같은 규율이다.

`web/page.html` 은 **템플릿이고 수치가 하나도 없다.** 이 스크립트가 주입해 `index.html` 을
만든다. `fetch` 는 `file://` 에서 막히므로 주입이어야 하고, 그래야 심사위원이 클론해서
더블클릭만 해도 열린다.

    python3 src/export_web.py
"""
import json, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
OPEN, CLOSE = "/*DATA_START*/", "/*DATA_END*/"
YEARS = list(range(1996, 2027))


def holders_by_year(spans):
    """연도별 보유 회사 수. 화면의 밴드 차트가 이걸 그린다."""
    per = []
    for y in YEARS:
        eo, so = f"{y}-12-31", f"{y}-01-01"
        per.append(len({c for c, s, e in spans if s and s <= eo and (not e or e >= so)}))
    return per


def main():
    D = json.load(open(os.path.join(ROOT, "data", "molecules.json"), encoding="utf-8"))
    M = D["molecules"]
    today = D["generated_for"]

    # 지금 팔리는 것만 화면에 올린다. 사라진 6,651개는 **코호트 통계로만** 쓴다 —
    # 한 줄씩 보여 줄 만한 정보가 없고(브랜드명뿐), 5 MB 를 4배로 불린다.
    rows = []
    for key, v in M.items():
        if not v["now"]:
            continue
        rows.append({
            "m": key,
            "n": v["now"], "e": v["ever"],
            "c": v["companies_now"][:8],
            "f": (v["first_marketed"] or "")[:4],
            "rx": 1 if v["rx"] else 0,
            "p": 1 if v["protected"] else 0,
            "L": 1 if v["patent_listed"] else 0,
            "b": v["brands"][:3],
            "y": holders_by_year(v["spans"]),
        })
    rows.sort(key=lambda r: (-(r["e"] - r["n"]), r["m"]))

    cohorts = {}
    for year in (2006, 2011, 2016):
        eo, so = f"{year}-12-31", f"{year}-01-01"
        agg = defaultdict(lambda: [0, 0])
        for v in M.values():
            h = len({c for c, s, e in v["spans"] if s and s <= eo and (not e or e >= so)})
            if not h:
                continue
            k = "1" if h == 1 else "2" if h == 2 else "3-5" if h <= 5 else "6+"
            agg[k][0] += 1
            if not v["now"]:
                agg[k][1] += 1
        cohorts[str(year)] = {k: {"n": t, "gone": g} for k, (t, g) in agg.items()}

    payload = {
        "today": today,
        "years": YEARS,
        "rows": rows,
        "cohorts": cohorts,
        "dark_total": sum(1 for v in M.values() if not v["now"]),
        "provenance": D["provenance"],
        "patent_register": D["patent_register"],
        # 우리를 반박하는 공표 수치. **UI 안에 둔다** — README 에만 두면 아무도 안 읽는다.
        "against": {
            "shortage": "PMPRB (2022): of 8,558 shortage reports, only 2 % were single-source "
                        "non-patented drugs. Single-source drugs were in shortage 22 % of the "
                        "time versus 32 % for multi-source. One supplier does not mean you will run out.",
            "published": "The count itself is published: PMPRB / Gaudette et al., JAMA Health "
                         "Forum 2024 report 52 % of off-patent drugs in Canada in a monopoly "
                         "market in 2022. We do not claim the count. We claim what it predicts.",
            "patent": "Only a minority of marketed DINs ever appear on the Patent Register. "
                      "“No listed patent” is not “off patent”.",
            "holder": "company_name is the market authorisation holder, not the plant. "
                      "Merging subsidiaries can only raise the single-supplier count, so these "
                      "numbers are the conservative direction.",
        },
    }
    os.makedirs(WEB, exist_ok=True)
    json.dump(payload, open(os.path.join(WEB, "data.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    tpl_path = os.path.join(WEB, "page.html")
    if not os.path.exists(tpl_path):
        print(f"  web/data.json 작성 ({len(rows):,}행). 템플릿이 없어 index.html 은 건너뛴다")
        return
    tpl = open(tpl_path, encoding="utf-8").read()
    if OPEN not in tpl or CLOSE not in tpl:
        raise SystemExit(f"템플릿에 {OPEN} … {CLOSE} 표시가 없다")
    head, rest = tpl.split(OPEN, 1)
    _old, tail = rest.split(CLOSE, 1)
    out = head + OPEN + "\nconst DATA = " + json.dumps(payload, ensure_ascii=False,
                                                       separators=(",", ":")) + ";\n" + CLOSE + tail
    open(os.path.join(WEB, "index.html"), "w", encoding="utf-8").write(out)
    kb = os.path.getsize(os.path.join(WEB, "index.html")) // 1024
    print(f"  web/data.json + web/index.html 작성 ({len(rows):,}행 · {kb:,} KB)")


if __name__ == "__main__":
    main()
