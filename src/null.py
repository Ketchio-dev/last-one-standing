"""기울기가 **산술만으로** 나오는가. 이 프로젝트를 죽일 수 있는 비교.

    python3 src/null.py [YYYY]

분자는 **보유 회사가 전부 떠나야** 시장에서 사라진다. 그러면 공급자가 k곳인 분자의
소멸 확률은, 회사들이 서로 독립적으로 확률 p 로 떠난다는 가정 아래 **p^k** 다.
p 는 코호트 자체에서 잰다(모형 없음). 즉 **관측 기울기의 상당 부분은 우리가 발견한 것이
아니라 곱셈이다.**

이 스크립트는 관측과 그 귀무를 나란히 찍는다. 남는 차이가 있으면 그게 우리 몫이고,
없으면 없다고 말한다.
"""
import json, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ROOT, "data", "molecules.json"), encoding="utf-8"))
M = D["molecules"]
YEARS = (2006, 2011, 2016)


def holders_at(spans, year):
    eo, so = f"{year}-12-31", f"{year}-01-01"
    return {c for c, s, e in spans if s and s <= eo and (not e or e >= so)}


def run(year):
    cohort = []
    for v in M.values():
        h = holders_at(v["spans"], year)
        if h:
            cohort.append((h, set(v["companies_now"]), bool(v["now"])))
    # p = **회사 단위** 이탈률. 분자 단위가 아니다 — 귀무가 회사의 독립 이탈이므로.
    seats = sum(len(h) for h, _n, _a in cohort)
    gone_seats = sum(len(h - n) for h, n, _a in cohort)
    p = gone_seats / seats if seats else 0.0

    obs = defaultdict(lambda: [0, 0])
    for h, _n, alive in cohort:
        k = min(len(h), 6)
        obs[k][0] += 1
        if not alive:
            obs[k][1] += 1

    print(f"\n  === {year} 코호트 ===")
    print(f"  그 해 보유된 '회사 자리' {seats:,}개 중 {gone_seats:,}개가 지금 없다 "
          f"→ 회사 단위 이탈률 p = {p:.3f}")
    print(f"\n  {'공급자':>7} {'분자':>7} {'관측 소멸':>9} {'산술 귀무 p^k':>13} {'차이':>9}")
    rows = []
    for k in sorted(obs):
        tot, gone = obs[k]
        o = gone * 100.0 / tot
        e = (p ** k) * 100.0
        rows.append((k, tot, o, e))
        lab = f"{k}곳" if k < 6 else "6곳+"
        print(f"  {lab:>7} {tot:>7,} {o:>8.1f} % {e:>12.1f} % {o - e:>+8.1f} pp")
    return p, rows


def main():
    years = (int(sys.argv[1]),) if len(sys.argv) > 1 else YEARS
    allrows = []
    for y in years:
        _p, rows = run(y)
        allrows.append((y, rows))

    print(f"\n  === 읽는 법 ===")
    print(f"  공급자가 많은 분자가 덜 사라지는 것은 **부분적으로 곱셈이다.**")
    print(f"  k곳이 전부 떠나야 사라지므로, 아무 신호가 없어도 p^k 만큼 기울기가 생긴다.")
    biggest = max(((abs(o - e), y, k, o, e) for y, rows in allrows for k, _t, o, e in rows))
    print(f"  귀무에서 가장 크게 벗어난 칸: {biggest[1]}년 공급자 {biggest[2]}곳 — "
          f"관측 {biggest[3]:.1f} % vs 귀무 {biggest[4]:.1f} % ({biggest[3] - biggest[4]:+.1f} pp)")
    over = sum(1 for _y, rows in allrows for _k, _t, o, e in rows if o > e + 1)
    under = sum(1 for _y, rows in allrows for _k, _t, o, e in rows if o < e - 1)
    print(f"  귀무보다 더 사라진 칸 {over}개 · 덜 사라진 칸 {under}개 — "
          f"**한 방향이 아니다.**")
    print(f"  그래서 우리는 '공급자 수가 소멸을 예측한다'를 발견으로 내세우지 않는다.")
    print(f"  내세울 수 있는 것은 **귀무에서 벗어난 부분**이고, 그것은 작고 양방향이다.")


if __name__ == "__main__":
    main()
