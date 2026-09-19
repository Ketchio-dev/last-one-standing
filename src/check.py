"""이 프로젝트가 주장하는 수가 실제로 스크립트 출력에서 나오는지 본다.

**분모 고정.** 어떤 실패에도 검사 개수가 줄지 않는다. 조건문 안에 검사를 두지 않는다.
검사 이름으로 고른다 — 인덱스로 고르면 항목을 끼울 때 라벨과 결과가 한 칸씩 어긋난다.

    python3 src/check.py
"""
import json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "molecules.json")
README = os.path.join(ROOT, "README.md")

NAMES = [
    "molecules.json 이 있다",
    "build.py 가 종료 코드 0",
    "report.py 가 종료 코드 0",
    "분자 수가 8,000개 이상이다",
    "시판 중 분자 수가 보고서 출력과 일치한다",
    "단일공급 수와 비율이 보고서 출력과 일치한다",
    "시장 이탈(한때 둘 이상) 수가 보고서 출력과 일치한다",
    "특허 미만료 수가 0이 아니다",
    "특허 만료일이 ISO 형식이다",
    "묶은 구간 소멸률이 공급자 수에 따라 단조 감소한다(세 코호트 전부)",
    "잘게 쪼갠 구간의 역전을 보고서가 직접 이름 부른다",
    "README 의 헤드라인 수치가 보고서 출력과 일치한다",
    "README 가 PMPRB 반증을 인용한다",
    "출처 기록에 특허 등록부 Last-Modified 가 있다",
    "화면용 데이터에 손으로 적은 수가 없다",
    "index.html 이 **이번 실행에서** 다시 쓰였고 데이터가 주입돼 있다",
    "model.py 가 종료 코드 0",
    "모델이 학습 연도보다 **뒤** 코호트로 시험된다",
    "모델 AUC 옆에 기준선(공급자 수 하나) AUC 가 같이 찍힌다",
    "보고서의 모델 절이 model.py 출력과 일치한다",
    "README 의 모델 수치가 model.py 출력과 일치한다",
    "null.py 가 종료 코드 0",
    "보고서가 산술 귀무(p^k)를 기울기 **옆에** 찍는다",
    "모델 특징이 코호트 연도 이후 정보를 쓰지 않는다",
    "README 가 말하는 검사·사보타주 개수가 실제와 같다",
    "제출물(devpost·1쪽 PDF)의 수치가 출력과 일치한다",
]
result = {n: (False, "실행되지 않음") for n in NAMES}
assert len(NAMES) == len(set(NAMES)), "검사 이름이 중복된다"


def NAME(n):
    if n not in result:
        raise SystemExit(f"검사 이름이 목록에 없다: {n!r}")
    return n


def ok(name, cond, detail=""):
    result[name] = (bool(cond), detail)


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "src", script), *args],
                       capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout, r.stderr


def one(pat, text, flags=0):
    m = re.search(pat, text, flags)
    return m.groups() if m else None


ok(NAME("molecules.json 이 있다"), os.path.exists(DATA), "없으면 python3 src/build.py")

rc_b, out_b, err_b = run("build.py")
ok(NAME("build.py 가 종료 코드 0"), rc_b == 0, err_b.strip()[-160:])
rc_r, out, err_r = run("report.py")
ok(NAME("report.py 가 종료 코드 0"), rc_r == 0, err_r.strip()[-160:])

D = json.load(open(DATA, encoding="utf-8")) if os.path.exists(DATA) else {"molecules": {}}
M = D.get("molecules", {})
alive = {k: v for k, v in M.items() if v["now"]}
ok(NAME("분자 수가 8,000개 이상이다"), len(M) >= 8000, f"실제 {len(M):,}")

# 보고서 출력을 **파싱해서** 대조한다. 여기서 다시 계산하지 않는다 —
# 검사가 자기가 계산한 값과 비교하면 스크립트가 틀려도 통과한다.
g = one(r"팔리는 분자 ([\d,]+)개", out)
ok(NAME("시판 중 분자 수가 보고서 출력과 일치한다"),
   bool(g) and int(g[0].replace(",", "")) == len(alive),
   f"보고서 {g[0] if g else '?'} vs 데이터 {len(alive):,}")

g = one(r"공급자가 하나뿐\s+([\d,]+) / ([\d,]+)\s+([\d.]+) %", out)
n_one = sum(1 for v in alive.values() if v["now"] == 1)
ok(NAME("단일공급 수와 비율이 보고서 출력과 일치한다"),
   bool(g) and int(g[0].replace(",", "")) == n_one
   and abs(float(g[2]) - n_one * 100.0 / max(len(alive), 1)) < 0.05,
   f"보고서 {g[0] if g else '?'} / {g[2] if g else '?'} % vs 데이터 {n_one:,}")

g = one(r"한때 둘 이상이었다가 하나가 된 분자\s+([\d,]+)", out)
thin = sum(1 for v in alive.values() if v["now"] == 1 and v["ever"] > 1)
ok(NAME("시장 이탈(한때 둘 이상) 수가 보고서 출력과 일치한다"),
   bool(g) and int(g[0].replace(",", "")) == thin,
   f"보고서 {g[0] if g else '?'} vs 데이터 {thin:,}")

# **0 은 그럴듯하게 생겼다.** 날짜 형식을 틀렸을 때 정확히 0 이 나왔다.
g = one(r"미만료 특허가 등록된\*\* 분자\s+([\d,]+)", out)
n_prot = int(g[0].replace(",", "")) if g else 0
ok(NAME("특허 미만료 수가 0이 아니다"), n_prot > 0,
   "0 이면 날짜 파싱을 의심한다 — MM/DD/YYYY 를 ISO 로 안 바꾸면 전부 만료로 찍힌다")

# **빈 집합에서 참이 되는 검사는 검사가 아니다.** 날짜 파싱을 통째로 꺼 봤더니
# 만료일이 하나도 안 생겼고, "어긋난 값 0개"로 이 검사가 통과했다.
# 그래서 "형식이 맞다" 앞에 "값이 있기는 하다" 를 먼저 건다.
have = [v["patent_max_expiry"] for v in M.values() if v.get("patent_max_expiry")]
bad_fmt = [x for x in have if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x)]
ok(NAME("특허 만료일이 ISO 형식이다"), len(have) >= 100 and not bad_fmt,
   f"만료일 있는 분자 {len(have)}개 · 형식 어긋남 {len(bad_fmt)}개 {bad_fmt[:3]}")

# 단조성은 이 프로젝트의 **주장 그 자체**다. 깨지면 헤드라인을 다시 써야 한다.
# 주장은 **묶은 구간의 기울기**다. 잘게 쪼갠 구간은 표본이 작아 뒤집힌다 —
# 구간을 골라 단조를 만들어 내는 대신, 주장하는 것만 검사하고 흔들림은 따로 검사한다.
breaks, named = [], []
blocks = re.findall(r"년 말 기준.*?(?=\n\n|\Z)", out, re.S)
if len(blocks) < 3:
    breaks.append(f"코호트 블록을 {len(blocks)}개만 읽었다")
for block in blocks:
    coarse = [float(x) for x in re.findall(r"([\d.]+) %\(n=", block)]
    if len(coarse) != 4:
        breaks.append(f"묶은 구간을 4개로 못 읽었다({len(coarse)})")
    elif any(b > a + 0.05 for a, b in zip(coarse, coarse[1:])):
        breaks.append(f"{coarse}")
    fine = [float(x) for x in re.findall(r"사라짐\s+([\d.]+) %", block)]
    has_inv = any(b > a + 0.05 for a, b in zip(fine, fine[1:]))
    says_inv = "역전: 없음" not in block
    if has_inv != says_inv:
        named.append(f"역전 {'있는데 말 안 함' if has_inv else '없는데 있다고 함'}")
ok(NAME("묶은 구간 소멸률이 공급자 수에 따라 단조 감소한다(세 코호트 전부)"), not breaks, "; ".join(breaks[:2]))
ok(NAME("잘게 쪼갠 구간의 역전을 보고서가 직접 이름 부른다"), not named, "; ".join(named[:2]))

readme = open(README, encoding="utf-8").read() if os.path.exists(README) else ""
pairs = []
for label, pat_out, pat_doc in (
    ("단일공급", r"공급자가 하나뿐\s+([\d,]+)", r"\*\*([\d,]+) of [\d,]+\*\* molecules have exactly one"),
    ("시장 이탈", r"한때 둘 이상이었다가 하나가 된 분자\s+([\d,]+)", r"\*\*([\d,]+)\*\* of them once had two or more"),
):
    a, b = one(pat_out, out), one(pat_doc, readme)
    if not (a and b and a[0] == b[0]):
        pairs.append(f"{label}: 출력 {a[0] if a else '?'} vs README {b[0] if b else '?'}")
ok(NAME("README 의 헤드라인 수치가 보고서 출력과 일치한다"), not pairs, "; ".join(pairs))

ok(NAME("README 가 PMPRB 반증을 인용한다"),
   "PMPRB" in readme and "22 %" in readme and "32 %" in readme,
   "우리를 반증하는 공표 수치를 README 에 싣지 않으면 심사위원이 먼저 찾는다")

pv = D.get("provenance", {})
lm = (pv.get("patent_zip") or {}).get("last_modified", "")
ok(NAME("출처 기록에 특허 등록부 Last-Modified 가 있다"), bool(lm), lm or "비어 있다")

tpl = os.path.join(ROOT, "web", "page.html")
nums = []
if os.path.exists(tpl):
    body = open(tpl, encoding="utf-8").read()
    body = re.sub(r"<style>.*?</style>", "", body, flags=re.S)   # CSS 의 수는 수치가 아니다
    nums = sorted({n for n in re.findall(r"\b\d+\.\d+\b", body)})
ok(NAME("화면용 데이터에 손으로 적은 수가 없다"),
   os.path.exists(tpl) and not nums,
   f"템플릿에 남은 소수 {nums[:6]}" if nums else ("web/page.html 이 아직 없다" if not os.path.exists(tpl) else ""))

# 템플릿에 수치가 없는 것과, **화면에 데이터가 실제로 들어간 것**은 다른 일이다.
# 주입을 건너뛰면 템플릿은 여전히 깨끗하고 페이지는 빈 채로 나간다.
# **디스크에 있는 것을 검사하면 안 된다.** 옛 index.html 이 남아 있으면, 생성기를
# 통째로 망가뜨려도 검사가 초록이다. 실제로 그랬다 — 주입을 건너뛰게 만든 사보타주를
# 놓쳤고, 원인은 검사가 export_web.py 를 **안 돌린 것**이었다.
# 그래서 이번 실행에서 다시 쓰게 하고, 그 파일을 본다.
idx = os.path.join(ROOT, "web", "index.html")
before = os.path.getmtime(idx) if os.path.exists(idx) else 0
time.sleep(1.1)
rc_w, _ow, err_w = run("export_web.py")
why = ""
good_idx = False
if rc_w != 0:
    why = f"export_web.py 가 실패했다: {err_w.strip()[-120:]}"
elif not os.path.exists(idx):
    why = "web/index.html 이 없다"
elif os.path.getmtime(idx) <= before:
    why = "export_web.py 를 돌렸는데 index.html 이 갱신되지 않았다 — 옛 화면이 남아 있다"
else:
    body = open(idx, encoding="utf-8").read()
    n_rows = len(re.findall(r'"m":"', body))
    if "const DATA = null" in body or n_rows < 100:
        why = f"주입된 행이 {n_rows}개다"
    else:
        good_idx, why = True, f"{n_rows:,}행 주입됨"
ok(NAME("index.html 이 **이번 실행에서** 다시 쓰였고 데이터가 주입돼 있다"), good_idx, why)

# --- 모델 ---
# 모델을 기준선 없이 보고하는 것이 이 프로젝트가 비판하는 바로 그 실패다.
# 그래서 "모델이 몇 점이냐"가 아니라 **"기준선이 옆에 있느냐"**를 검사한다.
rc_m, out_m, err_m = run("model.py")
ok(NAME("model.py 가 종료 코드 0"), rc_m == 0, err_m.strip()[-150:])

tr = re.search(r"=== 모델: (\d{4}) 코호트로 학습", out_m)
tests = [int(x) for x in re.findall(r"^\s{2}(\d{4})\s+[\d,]+\s+[\d,]+", out_m, re.M)]
ok(NAME("모델이 학습 연도보다 **뒤** 코호트로 시험된다"),
   bool(tr) and tests and all(t > int(tr.group(1)) for t in tests),
   f"학습 {tr.group(1) if tr else '?'} · 시험 {tests}"
   " — 같은 해를 섞으면 미래를 보고 과거를 맞히는 셈이다")

rows_m = re.findall(r"^\s{2}\d{4}\s+[\d,]+\s+[\d,]+\s+([\d.]+)\s+([\d.]+)\s+([+-][\d.]+)", out_m, re.M)
sys.path.insert(0, os.path.join(ROOT, "src"))
indep_base = []
try:
    import importlib
    _mod = importlib.import_module("model")
    for _y in _mod.TEST_YEARS:
        _te = _mod.cohort(_y)
        indep_base.append(round(_mod.auc([-r["x"][0] for r in _te], [r["y"] for r in _te]), 3))
except Exception as _e:                                   # 못 구하면 검사는 실패해야 한다
    indep_base = []
printed_base = [round(float(b_), 3) for b_, _m, _d in rows_m]
ok(NAME("모델 AUC 옆에 기준선(공급자 수 하나) AUC 가 같이 찍힌다"),
   len(rows_m) >= 2 and "공급자 수만" in out_m
   and indep_base and printed_base == indep_base
   and all(abs((float(m_) - float(b_)) - float(d_)) < 0.002 for b_, m_, d_ in rows_m),
   f"찍힌 기준선 {printed_base} vs 검사가 직접 구한 것 {indep_base}")

# 보고서는 model.py 출력을 **옮기기만** 해야 한다. 다시 계산하면 두 수가 갈린다.
rep_rows = re.findall(r"^\s+\[모델\]\s+\d{4}\s+[\d,]+\s+[\d,]+\s+([\d.]+)\s+([\d.]+)\s+([+-][\d.]+)", out, re.M)
ok(NAME("보고서의 모델 절이 model.py 출력과 일치한다"),
   len(rep_rows) >= 2 and rep_rows == rows_m,
   f"보고서 {rep_rows[:2]} vs 모델 {rows_m[:2]}")

# README 도 model.py 출력에 묶는다. 안 그러면 모델을 손보는 순간 문서만 낡는다.
rm_gain = one(r"better by \*\*([+-][\d.]+) AUC\*\*", readme)
mo_gain = one(r"AUC ([+-][\d.]+) 나았다", out_m)
rm_w = dict(re.findall(r"^\| `(\w+)` \| ([+-][\d.]+) \|$", readme, re.M))
mo_w = dict(re.findall(r"^\s{4}(\w+)\s+([+-][\d.]+)$", out_m, re.M))
ok(NAME("README 의 모델 수치가 model.py 출력과 일치한다"),
   bool(rm_gain and mo_gain and rm_gain[0] == mo_gain[0]) and rm_w == mo_w and len(mo_w) >= 5,
   f"AUC 차 README {rm_gain[0] if rm_gain else '?'} vs 출력 {mo_gain[0] if mo_gain else '?'} · "
   f"가중치 {len(rm_w)}개 vs {len(mo_w)}개 {'일치' if rm_w == mo_w else '불일치'}")

# --- 산술 귀무 ---
# 이 기울기의 상당 부분은 곱셈이다(k곳이 전부 떠나야 사라진다). 그걸 안 찍으면
# 우리가 발견하지 않은 것을 발견이라고 말하는 셈이다.
rc_n, out_n, err_n = run("null.py")
ok(NAME("null.py 가 종료 코드 0"), rc_n == 0, err_n.strip()[-150:])

null_rows = re.findall(r"([\d.]+) %\s+([\d.]+) %\s+([+-][\d.]+) pp", out_n)
# **검사가 p^k 를 직접 구한다.** 세 수의 자기 일관성만 보면 `e = o` 로 바꿔도 통과한다.
# 그리고 보고서가 **자기 문장으로** 귀무를 설명하는지도 본다 — 표만 echo 하면
# 독자는 그게 귀무인 줄 모른다.
mp = re.search(r"이탈률 p = ([\d.]+)", out_n)
indep_e = [round(float(mp.group(1)) ** k * 100.0, 1) for k in range(1, 7)] if mp else []
printed_e = [round(float(e), 1) for _o, e, _d in null_rows[:6]]
# **보고서 안에 실제로 실렸는지**를 본다. null.py 가 표를 만들 수 있다는 것과
# 보고서가 그것을 싣는다는 것은 다른 일이다 — 절을 통째로 빼도 초록이었다.
rep_null = re.findall(r"([\d.]+) %\s+([\d.]+) %\s+([+-][\d.]+) pp", out)
ok(NAME("보고서가 산술 귀무(p^k)를 기울기 **옆에** 찍는다"),
   len(rep_null) >= 6 and
   # p 를 소수 셋째 자리로 찍으므로 재계산이 0.1 pp 안쪽에서 어긋난다.
   # 정확히 같기를 요구하면 무고한 실패가 된다. 그래도 `e = o`(차이 0) 는
   # 10 pp 넘게 벌어지므로 이 허용 오차로 잡힌다.
   len(null_rows) >= 6 and indep_e
   and all(abs(a - b) < 0.3 for a, b in zip(printed_e, indep_e))
   and all(abs((float(o) - float(e)) - float(d)) < 0.15 for o, e, d in null_rows)
   and "보유 회사가 전부 떠나야" in out,
   f"찍힌 귀무 {printed_e} vs 검사가 직접 구한 {indep_e} · "
   f"보고서 설명 {'있음' if '보유 회사가 전부 떠나야' in out else '없음'}")

# 특징이 코호트 연도 이후를 보면 '예측'이 아니다. 소스에서 확인한다.
msrc = open(os.path.join(ROOT, "src", "model.py"), encoding="utf-8").read()
leaks = []
if re.search(r'min\(len\(v\["spans"\]\)', msrc):
    leaks.append("n_products 가 전체 spans 를 센다")
if '"patent_listed"' in msrc and "FEATURES" in msrc and "patent_listed" in msrc.split("FEATURES")[1][:200]:
    leaks.append("patent_listed 는 오늘의 등록부다")
ok(NAME("모델 특징이 코호트 연도 이후 정보를 쓰지 않는다"), not leaks, "; ".join(leaks))

# README 가 "16 checks" 라고 적어 두고 실제로는 24개인 채로 지내고 있었다.
# 숫자를 손으로 고치면 또 어긋난다. **권위값은 NAMES 와 SABS 이고**, README 를 거기에 묶는다.
# sabotage.py 를 **실행하지 않고** SABS 만 읽는다.
# 처음엔 모듈을 불러와서 읽었다가 포크 폭탄을 만들었다 — sabotage.py 에는 __main__ 가드가 없어서
# 불러오는 순간 사보타주 전체가 돌고, 그게 다시 이 파일을 부른다.
import ast as _ast
def _read_sabs():
    _src = open(os.path.join(ROOT, "src", "sabotage.py"), encoding="utf-8").read()
    for _n in _ast.parse(_src).body:
        if isinstance(_n, _ast.Assign) and any(getattr(_t, "id", "") == "SABS" for _t in _n.targets):
            return len(_ast.literal_eval(_n.value))
    return None
try:
    n_sabs = _read_sabs()
except Exception:
    n_sabs = None

_rd = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
_said_chk = one(r"check\.py\s*#\s*(\d+)\s*checks", _rd)
_said_sab = one(r"sabotage\.py\s*#\s*break\s*(\d+)\s*things", _rd)
_bad = []
if n_sabs is None:
    _bad.append("sabotage.py 에서 SABS 를 못 읽었다")
if not _said_chk:
    _bad.append("README 에 'check.py # N checks' 가 없다")
elif int(_said_chk[0]) != len(NAMES):
    _bad.append(f"README 는 검사 {_said_chk[0]}개라는데 실제 {len(NAMES)}개")
if not _said_sab:
    _bad.append("README 에 'sabotage.py # break N things' 가 없다")
elif n_sabs is not None and int(_said_sab[0]) != n_sabs:
    _bad.append(f"README 는 사보타주 {_said_sab[0]}개라는데 실제 {n_sabs}개")
ok(NAME("README 가 말하는 검사·사보타주 개수가 실제와 같다"), not _bad, "; ".join(_bad))

# 제출물도 표류한다. devpost 본문과 1쪽 PDF 원본을 **둘 다** 본다 —
# PDF 만 고치고 본문을 안 고치는 실수가 제일 흔하다.
#
# **자리에 묶는다. "문서 어딘가에 그 숫자가 있는가"로는 안 된다.** 첫 판본이 그렇게 했고,
# 407 을 470 으로 바꾸는 사보타주를 그대로 통과시켰다 — 다른 문장에 407 이 또 있었기 때문이다.
# (grid-clock 의 devpost 가 "3 a.m." 을 여섯 군데 남긴 채 지나간 것과 같은 병이다.)
_SUB = os.path.join(ROOT, "submission")
_sb = []
_FACTS = (
    ("시판 분자",   r"팔리는 분자 ([\d,]+)개",
     r"molecules currently marketed \(active-ingredient sets\) \| \*\*([\d,]+)\*\*",
     r"molecules currently marketed</td><td class=\"big\">([\d,]+)</td>"),
    ("단일공급",     r"공급자가 하나뿐\s+([\d,]+)",
     r"with exactly one supplier \| ([\d,]+) \(",
     r"with exactly one supplier</td><td><b>([\d,]+)</b>"),
    ("시장 이탈",   r"한때 둘 이상이었다가 하나가 된 분자\s+([\d,]+)",
     r"of those, once had two or more \| \*\*([\d,]+)\*\*",
     r"of those, once had two or more</td><td class=\"big\">([\d,]+)</td>"),
    ("미만료 특허", r"\*\*미만료 특허가 등록된\*\* 분자\s+([\d,]+)",
     r"unexpired listed patent \| ([\d,]+) \|",
     r"unexpired listed patent</td><td>([\d,]+)</td>"),
    ("등록부 전체", r"\*\*한 번이라도 오른\*\* 분자\s+([\d,]+)",
     r"Patent Register at all \| ([\d,]+) \|",
     r"Patent Register at all</td><td>([\d,]+)</td>"),
    ("2006 이전",   r"그중 2006년 이전부터 팔리던 것\s+([\d,]+)",
     r"before 2006, one supplier \| \*\*([\d,]+)\*\*",
     r"pre-2006, one supplier</td><td>([\d,]+)</td>"),
    ("사라진 분자", r"시판 중이 아닌 분자 ([\d,]+)개",
     r"once marketed in Canada and no longer \| \*\*([\d,]+)\*\*",
     r"once marketed in Canada, no longer</td><td>([\d,]+)</td>"),
)
_texts = {}
for _n in ("devpost.md", "onepager.html"):
    _f = os.path.join(_SUB, _n)
    if not os.path.exists(_f):
        _sb.append(f"{_n} 가 없다")
    else:
        _texts[_n] = open(_f, encoding="utf-8").read()
_seen = 0
for _label, _po, _pdev, _pone in _FACTS:
    _a = one(_po, out)
    if not _a:
        _sb.append(f"{_label}: report 출력에서 못 읽었다"); continue
    for _n, _pat in (("devpost.md", _pdev), ("onepager.html", _pone)):
        if _n not in _texts: continue
        _b = one(_pat, _texts[_n])
        if not _b:
            _sb.append(f"{_label}: {_n} 의 그 자리를 못 찾았다")
        elif _a[0].replace(",", "") != _b[0].replace(",", ""):
            _sb.append(f"{_label}: 출력 {_a[0]} vs {_n} {_b[0]}")
        else:
            _seen += 1
# 빈 집합에 참이 되지 않게: 확인한 자리가 충분히 많아야 한다
if _seen < len(_FACTS) * 2 and not _sb:
    _sb.append(f"확인한 자리가 {_seen}개뿐이다 (기대 {len(_FACTS)*2})")
ok(NAME("제출물(devpost·1쪽 PDF)의 수치가 출력과 일치한다"), not _sb, "; ".join(sorted(set(_sb))[:4]))

print()
failed = 0
for n in NAMES:
    good, detail = result[n]
    failed += not good
    print(f"  {'OK ' if good else 'BAD'}  {n}" + ("" if good else f"   {detail}"))
print(f"\n{len(NAMES) - failed}/{len(NAMES)} 통과. (분모 고정 — 실패해도 개수가 줄지 않는다)")
sys.exit(1 if failed else 0)
