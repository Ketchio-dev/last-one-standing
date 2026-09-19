"""분자별 공급자 타임라인을 만든다. 여기가 이 프로젝트의 전부다.

    python3 src/build.py

**세는 단위를 먼저 못 박는다.** Health Canada 의 `ai_group_no` 는 성분만이 아니라
**함량·제형까지** 묶는다(리도카인이 1% 주사 / 2% 젤리 / 5% 연고로 세 그룹). 그래서
여기서는 **성분 집합**을 분자로 본다. 두 단위의 수가 다르고, 그 차이를 보고서가 같이 찍는다.

한 제품의 생존 구간:  original_market_date  →  (취소됐으면) history_date
`status` 는 제품당 한 줄이고 이력이 아니다 — 지금 상태와 그 상태가 된 날짜뿐이다.
그래서 이 구간은 **근사**다. 보고서가 그렇게 말한다.
"""
import csv, io, json, os, re, sys, zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import ROOT, fetch, load, provenance

OUT = os.path.join(ROOT, "data")
TODAY = "2026-09-16"          # 인자로 넘기면 바뀐다. 코드 안에 오늘을 숨기지 않는다.

# 회사명 꼬리표. 안 떼면 같은 회사가 둘로 세어진다.
SUFFIXES = (" INC.", " INC", " LTD.", " LTD", " ULC", " LLC", " CORP.", " CORP",
            " LIMITED", " COMPANY", " CO.", " L.P.", " LP", " S.A.", " A/S", ",")
RX = {"PRESCRIPTION", "ETHICAL", "PRESCRIPTION RECOMMENDED",
      "NARCOTICS (CDSA I)", "TARGETED SUBSTANCES (CDSA IV)",
      "CONTROLLED DRUGS (CDSA I)", "CONTROLLED DRUGS (CDSA III)",
      "CONTROLLED DRUGS (CDSA IV)"}
ALIVE = {"Marketed", "Approved", "Restricted Access"}


def norm_company(co):
    co = (co or "").strip().upper()
    for s in SUFFIXES:
        co = co.replace(s, " ")
    return " ".join(co.split()) or "(UNNAMED)"


def iso(us_date):
    """`MM/DD/YYYY` -> `YYYY-MM-DD`.

    **이 변환을 빼먹으면 조용히 0 이 나온다.** 실제로 그랬다 —
    `"08/30/2020" > "2026-09-16"` 은 문자열로 False 라서 *모든* 특허가 만료로 판정됐고,
    "단일공급 중 미만료 특허 0건" 이라는 그럴듯한 수가 찍혔다.
    '등록은 됐는데 만료됨' 을 따로 세어 나란히 찍지 않았으면 못 봤다.
    """
    t = (us_date or "").strip()
    if len(t) == 10 and t[2] == "/" and t[5] == "/":
        return f"{t[6:]}-{t[:2]}-{t[3:5]}"
    return ""


def read_patent_zip():
    """DIN -> 가장 늦은 특허 만료일. 등록부에 없는 DIN 은 **'만료'가 아니라 '없음'이다.**"""
    z = zipfile.ZipFile(fetch("patent_zip", quiet=True))

    def rows(member):
        raw = z.read(member).decode("utf-8-sig", errors="replace")
        # 레코드 사이에 빈 줄이 있다. 그대로 DictReader 에 넣으면 값이 전부 None 인
        # 유령 행이 나온다 — 그걸 세면 개수가 조용히 부풀어 오른다.
        return [r for r in csv.DictReader(io.StringIO(raw)) if r.get("DRUG_ID")]

    drugs = rows("drugs_e.txt")
    pats = rows("patent-service_e.txt")
    expiry = defaultdict(list)
    for p in pats:
        e = iso(p.get("EXPIRATION_DATE"))
        if e:
            expiry[p["DRUG_ID"]].append(e)
    din_expiry = {}
    for d in drugs:
        din = (d.get("DIN") or "").strip()
        if not din:
            continue
        exp = expiry.get(d["DRUG_ID"])
        if exp:
            din_expiry[din] = max(max(exp), din_expiry.get(din, ""))
    return din_expiry, len(drugs), len(pats)


def main():
    today = sys.argv[1] if len(sys.argv) > 1 else TODAY
    os.makedirs(OUT, exist_ok=True)

    marketed = [x for x in load("marketed", quiet=True) if x["class_name"] == "Human"]
    every = [x for x in load("all_products", quiet=True) if x["class_name"] == "Human"]
    ai = load("ingredients", quiet=True)
    status = {x["drug_code"]: x for x in load("status", quiet=True)}
    sched = defaultdict(set)
    for r in load("schedule", quiet=True):
        sched[r["drug_code"]].add((r.get("schedule_name") or "").strip().upper())
    din_expiry, n_pdrugs, n_pats = read_patent_zip()

    ing = defaultdict(set)
    for r in ai:
        ing[r["drug_code"]].add(r["ingredient_name"].strip().upper())

    marketed_codes = {x["drug_code"] for x in marketed}
    mols = defaultdict(lambda: {"now": set(), "ever": set(), "codes": [], "dins": set(),
                                "spans": [], "rx": False, "names": set()})
    skipped = 0
    for p in every:
        names = ing.get(p["drug_code"])
        if not names:
            skipped += 1
            continue
        key = " + ".join(sorted(names))
        m = mols[key]
        co = norm_company(p["company_name"])
        m["ever"].add(co)
        m["codes"].append(p["drug_code"])
        m["names"].add(p["brand_name"].strip())
        din = (p.get("drug_identification_number") or "").strip()
        if din:
            m["dins"].add(din)
        if p["drug_code"] in marketed_codes:
            m["now"].add(co)
        st = status.get(p["drug_code"]) or {}
        start = (st.get("original_market_date") or "")[:10]
        end = "" if st.get("status") in ALIVE else (st.get("history_date") or "")[:10]
        if start:
            m["spans"].append((co, start, end))
        if sched.get(p["drug_code"], set()) & RX:
            m["rx"] = True

    out = {}
    for key, m in mols.items():
        # **사라진 분자를 버리지 않는다.** `now == 0` 인 것이 이 프로젝트의 핵심 결과다 —
        # 공급자 수가 소멸을 예측하는지 보려면 소멸한 쪽이 있어야 한다.
        # 앞 판본은 여기서 걸러 냈고, 그러면 "소멸률"을 계산할 표본 자체가 사라진다.
        starts = [s for _c, s, _e in m["spans"]]
        prot = [din_expiry[d] for d in m["dins"] if d in din_expiry]
        listed = [d for d in m["dins"] if d in din_expiry]
        out[key] = {
            "now": len(m["now"]),
            "ever": len(m["ever"]),
            "companies_now": sorted(m["now"]),
            "first_marketed": min(starts) if starts else None,
            "rx": m["rx"],
            "patent_listed": len(listed),
            "patent_max_expiry": max(prot) if prot else None,
            "protected": bool(prot and max(prot) > today),
            "spans": [[c, s, e] for c, s, e in sorted(m["spans"], key=lambda t: t[1])],
            "brands": sorted(m["names"])[:6],
        }

    json.dump({"generated_for": today, "provenance": provenance(),
               "patent_register": {"drug_rows": n_pdrugs, "patent_rows": n_pats,
                                   "dins_with_expiry": len(din_expiry)},
               "molecules": out},
              open(os.path.join(OUT, "molecules.json"), "w", encoding="utf-8"),
              ensure_ascii=False)

    alive = sum(1 for v in out.values() if v["now"])
    print(f"  분자 {len(out):,}개 (시판 중 {alive:,} · 사라짐 {len(out)-alive:,}) · 성분 정보 없어 건너뛴 제품 {skipped:,}개")
    print(f"  특허 등록부: 약 {n_pdrugs:,}행 · 특허 {n_pats:,}행 · 만료일 있는 DIN {len(din_expiry):,}개")
    print(f"  data/molecules.json 작성")


if __name__ == "__main__":
    main()
