"""공급자 수 말고 **다른 것도** 소멸을 예측하는가. 의존성 0, 순수 파이썬.

    python3 src/model.py

설계가 곧 주장이다:
  · **시간으로 나눈다.** 2006 코호트로 학습하고 2011·2016 코호트로 시험한다.
    같은 해를 섞어 무작위로 쪼개면 미래를 보고 과거를 맞히는 셈이 된다.
  · **기준선이 '공급자 수 하나'다.** 모델이 그걸 못 이기면 모델은 장식이다.
    이 스크립트는 **못 이겼다는 결과도 그대로 찍는다.**
  · sklearn·numpy 를 쓰지 않는다. `python3` 하나로 재현된다는 것이 이 저장소의 주장이다.
"""
import json, math, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ROOT, "data", "molecules.json"), encoding="utf-8"))
M = D["molecules"]
TODAY = D["generated_for"]
TRAIN_YEAR, TEST_YEARS = 2006, (2011, 2016)

# **코호트 연도에 알 수 있는 것만 쓴다.**
# 앞 판본은 `n_products` 로 **그 해 이후에 나온 제품까지** 셌고(가장 큰 가중치였다),
# `patent_listed` 는 **오늘의** 특허 등록부를 봤다. 둘 다 미래를 보고 과거를 맞히는 것이다.
# `rx` 는 시점별 값을 만들 수 없어 오늘 값을 쓴다 — 그 사실을 출력이 밝힌다.
FEATURES = ["holders", "lost_already", "age_years", "products_by_then", "rx"]
LEAKY_KEPT = {"rx": "오늘의 처방/비처방 구분. 시점별 값이 DPD 에 없다."}


def holders_at(spans, year):
    eo, so = f"{year}-12-31", f"{year}-01-01"
    return {c for c, s, e in spans if s and s <= eo and (not e or e >= so)}


def peak_before(spans, year):
    eo = f"{year}-12-31"
    return len({c for c, s, _e in spans if s and s <= eo})


def cohort(year):
    """그 해 시판 중이던 분자 → (특징, 사라졌는가)."""
    rows = []
    for key, v in M.items():
        h = holders_at(v["spans"], year)
        if not h:
            continue
        fm = v.get("first_marketed") or ""
        age = (year - int(fm[:4])) if fm[:4].isdigit() else 0
        # 그 해까지 **시작된** 제품만 센다. 전체 spans 를 세면 미래가 새어 들어온다.
        started = sum(1 for _c, st, _e in v["spans"] if st and st <= f"{year}-12-31")
        rows.append({
            "key": key,
            "x": [len(h), max(0, peak_before(v["spans"], year) - len(h)),
                  max(0, min(age, 60)), min(started, 40), 1.0 if v["rx"] else 0.0],
            "y": 0.0 if v["now"] else 1.0,
        })
    return rows


def standardize(rows, stats=None):
    k = len(FEATURES)
    if stats is None:
        mu = [sum(r["x"][j] for r in rows) / len(rows) for j in range(k)]
        sd = [max(1e-9, math.sqrt(sum((r["x"][j] - mu[j]) ** 2 for r in rows) / len(rows)))
              for j in range(k)]
        stats = (mu, sd)
    mu, sd = stats
    for r in rows:
        r["z"] = [(r["x"][j] - mu[j]) / sd[j] for j in range(k)]
    return stats


def fit(rows, epochs=400, lr=0.25, l2=1e-3):
    k = len(FEATURES)
    w, b = [0.0] * k, 0.0
    n = len(rows)
    for _ in range(epochs):
        gw, gb = [0.0] * k, 0.0
        for r in rows:
            z = b + sum(w[j] * r["z"][j] for j in range(k))
            p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
            d = p - r["y"]
            gb += d
            for j in range(k):
                gw[j] += d * r["z"][j]
        b -= lr * gb / n
        for j in range(k):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
    return w, b


def score(rows, w, b):
    k = len(FEATURES)
    return [b + sum(w[j] * r["z"][j] for j in range(k)) for r in rows]


def auc(scores, labels):
    """순위 통계로 구한 AUC. 동점은 절반으로 센다."""
    pairs = sorted(zip(scores, labels))
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if not n_pos or not n_neg:
        return float("nan")
    # 동점 처리를 위해 평균 순위를 쓴다
    ranks, i = [0.0] * len(pairs), 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            ranks[t] = avg
        i = j + 1
    s = sum(r for r, (_sc, lab) in zip(ranks, pairs) if lab == 1.0)
    return (s - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def main():
    train = cohort(TRAIN_YEAR)
    stats = standardize(train)
    w, b = fit(train)

    print(f"\n  === 모델: {TRAIN_YEAR} 코호트로 학습, 이후 코호트로 시험 ===")
    print(f"  학습 {len(train):,}분자 (사라짐 {sum(r['y'] for r in train):,.0f})")
    print(f"  특징: {', '.join(FEATURES)}   (순수 파이썬 로지스틱 회귀, 의존성 0)")
    for f, why in LEAKY_KEPT.items():
        print(f"  주의: `{f}` 는 시점별 값이 아니다 — {why}")
    print(f"  라벨은 세 코호트 모두 **같은 끝점**(오늘 시판 중인가)이다. 그래서 이것은")
    print(f"  '미래를 예측한다'가 아니라 '그 해의 상태로 오늘을 설명한다'에 가깝다.")
    print(f"\n  학습된 가중치 — 부호가 방향을 말한다")
    for j, f in enumerate(FEATURES):
        print(f"    {f:<14} {w[j]:+7.3f}")

    print(f"\n  {'코호트':<8} {'분자':>7} {'사라짐':>7} {'공급자 수만':>12} {'모델':>8} {'차이':>8}")
    verdict = []
    for y in TEST_YEARS:
        te = cohort(y)
        standardize(te, stats)
        labels = [r["y"] for r in te]
        # 기준선: 공급자 수가 적을수록 위험하다는 것 하나만. 부호를 뒤집어 '위험 점수'로.
        base = auc([-r["x"][0] for r in te], labels)
        mod = auc(score(te, w, b), labels)
        verdict.append(mod - base)
        print(f"  {y:<8} {len(te):>7,} {sum(labels):>7,.0f} {base:>12.3f} {mod:>8.3f} {mod - base:>+8.3f}")

    gain = sum(verdict) / len(verdict)
    print()
    if gain < 0.01:
        print(f"  **모델이 공급자 수 하나를 이기지 못했다** (평균 AUC 차 {gain:+.3f}).")
        print(f"  그래서 제품에 모델을 싣지 않는다. 세는 것으로 충분하다 —")
        print(f"  그리고 그 사실 자체가 이 페이지가 보고하는 결과다.")
    else:
        print(f"  모델이 공급자 수 하나보다 AUC {gain:+.3f} 나았다.")
        print(f"  작다. 이 차이로 무엇을 바꿀 수 있는지 말할 수 없으면 싣지 않는다.")
    print(f"\n  읽는 법: AUC 0.5 는 동전 던지기다. 두 수를 나란히 두는 이유는")
    print(f"  '모델이 잘 맞혔다'가 아니라 **'모델이 세는 것보다 나았나'**가 질문이기 때문이다.")
    print(f"  특징은 {TRAIN_YEAR} 까지만 보고 학습했고 시험은 그 뒤 코호트다. 다만 **라벨은")
    print(f"  세 코호트가 공유한다** — 코호트끼리 독립이 아니고, 분자도 상당수 겹친다.")
    print(f"  그래서 '세 번 재현됐다'가 아니라 '같은 끝점을 세 시점에서 본 것'이다.")


if __name__ == "__main__":
    main()
