"""수치를 찍는다. **문서·화면·영상이 인용할 수 있는 유일한 출처.**

    python3 src/report.py [YYYY-MM-DD]

규율은 grid-clock 과 같다 — 여기서 나온 수만 다른 곳에 옮긴다. 다시 계산하지 않는다.
"""
import json, os, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ROOT, "data", "molecules.json"), encoding="utf-8"))
M = D["molecules"]
TODAY = sys.argv[1] if len(sys.argv) > 1 else D["generated_for"]

alive = {k: v for k, v in M.items() if v["now"]}
dark = {k: v for k, v in M.items() if not v["now"]}


def holders_at(v, year):
    """그 해 말에 이 분자를 들고 있던 회사 수."""
    end_of, start_of = f"{year}-12-31", f"{year}-01-01"
    return len({c for c, s, e in v["spans"] if s and s <= end_of and (not e or e >= start_of)})


def pct(a, b):
    return f"{a * 100.0 / b:5.1f} %" if b else "    — "


print(f"\n  === 지금 캐나다에서 팔리는 분자 {len(alive):,}개 ===")
print(f"  (성분 집합 기준. Health Canada 의 ai_group_no 는 함량·제형까지 묶으므로 더 잘게 쪼개진다)")
one = [k for k, v in alive.items() if v["now"] == 1]
print(f"\n  공급자가 하나뿐   {len(one):5,} / {len(alive):,}  {pct(len(one), len(alive))}")
dist = Counter(v["now"] for v in alive.values())
for n in sorted(dist)[:6]:
    print(f"    공급자 {n:2d}곳      {dist[n]:5,}       {pct(dist[n], len(alive))}")
big = sum(c for n, c in dist.items() if n > 6)
print(f"    7곳 이상       {big:5,}       {pct(big, len(alive))}")

print(f"\n  === 그 '하나'는 처음부터 하나였나 ===")
thinned = [k for k in one if alive[k]["ever"] > 1]
print(f"  한때 둘 이상이었다가 하나가 된 분자   {len(thinned):5,} / {len(one):,}  {pct(len(thinned), len(one))}")
print(f"  처음부터 한 회사뿐이었던 분자        {len(one) - len(thinned):5,} / {len(one):,}  "
      f"{pct(len(one) - len(thinned), len(one))}")
print(f"  → 앞의 것은 **측정된 시장 이탈**이다. 뒤의 것은 그냥 신약일 수 있다.")

print(f"\n  === 특허를 걷어 내면 ===")
prot = [k for k in one if alive[k]["protected"]]
listed = [k for k in one if alive[k]["patent_listed"]]
print(f"  단일공급 중 **미만료 특허가 등록된** 분자   {len(prot):5,}  {pct(len(prot), len(one))}")
print(f"  단일공급 중 등록부에 **한 번이라도 오른** 분자 {len(listed):5,}  {pct(len(listed), len(one))}")
print(f"  나머지 {len(one) - len(listed):,}개는 '특허 만료'가 아니라 **'등록된 특허 없음'**이다 —")
print(f"  등록부에 오른 적 없는 약(오래된 것, 생물의약품)이 여기 섞인다. 같은 말이 아니다.")

rx_one = [k for k in one if alive[k]["rx"] and not alive[k]["protected"]]
print(f"\n  처방전용 + 미만료 특허 없음 + 단일공급      {len(rx_one):5,}")
old_rx = [k for k in rx_one if (alive[k]["first_marketed"] or "9999") < "2006"]
print(f"  그중 2006년 이전부터 팔리던 것             {len(old_rx):5,}")
print(f"  → 이게 '제네릭이 들어올 수 있었는데 아무도 안 들어온' 자리다.")

print(f"\n  === 공급자 수가 소멸을 예측하는가 (코호트) ===")
print(f"  지금 시판 중이 아닌 분자 {len(dark):,}개가 표본의 반대편이다.")
for year in (2006, 2011, 2016):
    print(f"\n  {year}년 말 기준 — 그 해 시판 중이던 분자를 공급자 수로 나누고, "
          f"{TODAY[:4]}년 현재 사라진 비율")
    cohort = defaultdict(lambda: [0, 0])
    for k, v in M.items():
        h = holders_at(v, year)
        if h == 0:
            continue
        band = h if h <= 5 else 6
        cohort[band][0] += 1
        if not v["now"]:
            cohort[band][1] += 1
    rates = []
    for band in sorted(cohort):
        tot, gone = cohort[band]
        lab = f"{band}곳" if band <= 5 else "6곳 이상"
        r = gone * 100.0 / tot if tot else 0.0
        rates.append((lab, tot, r))
        print(f"    공급자 {lab:<8} 분자 {tot:5,}개 중 {gone:5,}개 사라짐   {pct(gone, tot)}")

    # **흔들림을 우리가 먼저 이름 부른다.** 잘게 쪼갠 구간은 표본이 작아 뒤집힌다.
    # 구간을 골라 단조를 만들어 내지 않는다 — 둘 다 찍고, 어디서 뒤집혔는지 말한다.
    inv = [f"{a[0]}({a[2]:.1f} %) < {b[0]}({b[2]:.1f} %)"
           for a, b in zip(rates, rates[1:]) if b[2] > a[2] + 0.05]
    print(f"    역전: {'; '.join(inv) if inv else '없음'}"
          + (f"  ← 표본 {min(t for l, t, r in rates if l in inv[0].split('(')[0]) if inv else ''}" if False else ""))

    coarse = {"1곳": [0, 0], "2곳": [0, 0], "3~5곳": [0, 0], "6곳 이상": [0, 0]}
    for band, (tot, gone) in cohort.items():
        key = "1곳" if band == 1 else "2곳" if band == 2 else "3~5곳" if band <= 5 else "6곳 이상"
        coarse[key][0] += tot
        coarse[key][1] += gone
    print(f"    묶어서: " + " · ".join(
        f"{k} {c[1] * 100.0 / c[0]:.1f} %(n={c[0]:,})" for k, c in coarse.items() if c[0]))

print(f"\n  === 이 기울기의 얼마가 산술인가 ===")
import subprocess as _sp2
_n = _sp2.run([sys.executable, os.path.join(ROOT, "src", "null.py"), "2016"],
              capture_output=True, text=True, timeout=300)
if _n.returncode != 0:
    print(f"  null.py 가 실패했다: {_n.stderr.strip()[-160:]}")
else:
    for line in _n.stdout.splitlines():
        if line.strip() and "읽는 법" not in line:
            print("  " + line.strip())
        if "읽는 법" in line:
            break
print(f"  → 분자는 **보유 회사가 전부 떠나야** 사라진다. 그러면 신호가 전혀 없어도")
print(f"     소멸률이 p^k 로 떨어진다. 위 기울기의 상당 부분이 그 곱셈이다.")
print(f"     우리가 내세울 수 있는 것은 **귀무에서 벗어난 부분**이고, 작고 양방향이다.")

print(f"\n  === 공급자 수 말고 무엇이 더 예측하는가 ===")
import subprocess as _sp
_m = _sp.run([sys.executable, os.path.join(ROOT, "src", "model.py")],
             capture_output=True, text=True, timeout=600)
if _m.returncode != 0:
    print(f"  model.py 가 실패했다: {_m.stderr.strip()[-160:]}")
else:
    # **여기서 다시 계산하지 않는다.** model.py 가 찍은 줄을 그대로 옮긴다.
    keep = False
    for line in _m.stdout.splitlines():
        if "코호트" in line and "공급자 수만" in line:
            keep = True
        if keep and line.strip():
            print("  [모델] " + line.strip())
        if "읽는 법" in line:
            break

print(f"\n  === 이 수치가 말하지 않는 것 ===")
print(f"  · 공급자가 하나라고 품절이 잦다는 뜻이 아니다. PMPRB(2022) 는 품절 신고 8,558건 중")
print(f"    단일공급·비특허가 2 %였고, 품절 비율도 단일공급 22 % < 다중공급 32 % 라고 보고했다.")
print(f"  · '사라졌다'는 대부분 구식화다. 같은 계열에 생존자가 있는지는 여기서 안 센다.")
print(f"  · company_name 은 **시판 허가권자**이지 제조소가 아니다. 계열사는 둘로 세어진다 —")
print(f"    병합하면 단일공급 수는 **늘어날 수만 있다**. 즉 위 수는 보수적이다.")
print(f"  · 제품 생존 구간은 근사다. DPD 의 status 는 이력이 아니라 **현재 상태 한 줄**이다.")

pv = D["provenance"]
print(f"\n  === 출처 ===")
for name, s in pv.items():
    lm = s["last_modified"] or "—"
    print(f"    {name:<14} {s['bytes']:>10,} B · 받음 {s['fetched_at']} · Last-Modified {lm}")
print(f"    특허 등록부는 정적 파일이다. **위 Last-Modified 가 이 분석의 특허 기준일이다.**")
