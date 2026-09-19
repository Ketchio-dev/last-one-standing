"""일부러 망가뜨린다. 검사가 알아채는가.

**통과 개수는 품질 지표가 아니다.** 15/15 는 "검사가 무언가를 잡는다"를 뜻하지 않는다.
어제 영상 검사가 12/12 를 찍으면서 통째로 무음인 장면을 통과시켰다.

    python3 src/sabotage.py
    python3 src/sabotage.py --only 특허      # 설명에 그 말이 들어간 것만

세 가지를 갈라 찍는다:
  검출 — 겨냥한 검사가 BAD 로 바뀌었다
  놓침 — 망가뜨렸는데 검사가 초록이다. **이게 진짜 결함이다**
  무효 — 겨냥할 자리를 못 찾았다. 코드가 바뀌었는데 이 파일이 안 따라간 것이다(검사 잘못이 아니다)
"""
import atexit, hashlib, io, os, re, shutil, signal, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 재진입 차단. check.py 가 이 파일을 **불러오기만** 했다가 포크 폭탄이 났다(가드가 없어서
# 불러오는 즉시 전체가 돌았고, 그게 다시 check.py 를 불렀다). 환경변수는 자식이 물려받으므로
# 어느 경로로 다시 들어와도 여기서 멈춘다.
if os.environ.get("SABOTAGE_RUNNING"):
    sys.exit("사보타주가 이미 돌고 있다 — 재진입을 막는다")
os.environ["SABOTAGE_RUNNING"] = "1"

# (설명, 파일, 찾을 것, 바꿀 것, 실패해야 하는 검사 이름의 일부)
# `re:` 로 시작하면 정규식이다. **코드가 세거나 자라는 것은 리터럴로 겨냥하지 않는다** —
# 목록이 늘면 조용히 무효가 된다.
SABS = [
    ("빌드가 즉시 실패", "src/build.py",
     "def main():", "def main():\n    raise SystemExit(7)",
     "build.py 가 종료 코드 0"),
    ("보고서가 즉시 실패", "src/report.py",
     "alive = {k: v for k, v in M.items() if v[\"now\"]}",
     "raise SystemExit(7)\nalive = {k: v for k, v in M.items() if v[\"now\"]}",
     "report.py 가 종료 코드 0"),
    ("사라진 분자를 버린다(코호트 표본이 사라진다)", "src/build.py",
     '        starts = [s for _c, s, _e in m["spans"]]',
     '        if not m["now"]:\n            continue\n'
     '        starts = [s for _c, s, _e in m["spans"]]',
     "분자 수가 8,000개 이상"),
    ("보고서가 시판 분자 수를 부풀려 찍는다", "src/report.py",
     "팔리는 분자 {len(alive):,}개", "팔리는 분자 {len(alive)+500:,}개",
     "시판 중 분자 수가 보고서 출력과"),
    ("보고서가 단일공급 수를 다시 계산해 틀리게 찍는다", "src/report.py",
     'one = [k for k, v in alive.items() if v["now"] == 1]',
     'one = [k for k, v in alive.items() if v["now"] <= 2]',
     "단일공급 수와 비율이 보고서 출력과"),
    ("시장 이탈 판정을 뒤집는다", "src/report.py",
     'thinned = [k for k in one if alive[k]["ever"] > 1]',
     'thinned = [k for k in one if alive[k]["ever"] > 0]',
     "시장 이탈(한때 둘 이상) 수가"),
    ("특허 만료일을 ISO 로 안 바꾼다(그럴듯한 0이 나온다)", "src/build.py",
     "        return f\"{t[6:]}-{t[:2]}-{t[3:5]}\"", "        return t",
     "특허 미만료 수가 0이 아니다"),
    ("만료일에 미국식 형식을 그대로 흘린다", "src/build.py",
     "    if len(t) == 10 and t[2] == \"/\" and t[5] == \"/\":",
     "    if False:",
     "특허 만료일이 ISO 형식"),
    ("묶은 구간을 caseload 대신 역순으로 찍는다", "src/report.py",
     '    print(f"    묶어서: " + " · ".join(',
     '    print(f"    묶어서: " + " · ".join(list(reversed([',
     "묶은 구간 소멸률이"),
    ("역전이 있는데 '없음'이라고 말한다", "src/report.py",
     "    print(f\"    역전: {'; '.join(inv) if inv else '없음'}\"",
     "    print(f\"    역전: {'없음'}\"",
     "역전을 보고서가 직접 이름"),
    ("README 의 단일공급 수를 손으로 고친다", "README.md",
     r"re:\*\*[\d,]+ of [\d,]+\*\* molecules have exactly one", "**9,999 of 2,044** molecules have exactly one",
     "README 의 헤드라인 수치가"),
    ("README 에서 PMPRB 반증을 지운다", "README.md",
     r"re:single-source drugs were in shortage \*\*22 %\*\*", "they were in shortage sometimes",
     "README 가 PMPRB 반증을"),
    # 받아 올 때만 기록하므로 캐시가 있으면 이 변경은 **동작을 안 바꾼다**.
    # 소비 지점(provenance)을 겨냥해야 검사가 실제로 걸린다.
    ("출처 기록에서 Last-Modified 를 버린다", "src/sources.py",
     "    return _stamps()",
     "    return {k: {**v, \"last_modified\": \"\"} for k, v in _stamps().items()}",
     "출처 기록에 특허 등록부 Last-Modified"),
    ("템플릿에 수치를 손으로 적는다", "web/page.html",
     "<h1>Some medicines have one company left standing behind them.</h1>",
     "<h1>58.9 % of medicines have one company left standing behind them.</h1>",
     "화면용 데이터에 손으로 적은 수가"),
    ("주입을 건너뛰어 index.html 을 빈 채로 둔다", "src/export_web.py",
     'out = head + OPEN + "\\nconst DATA = " + json.dumps(payload, ensure_ascii=False,\n                                                       separators=(",", ":")) + ";\\n" + CLOSE + tail',
     'out = tpl',
     "index.html 이 **이번 실행에서** 다시 쓰였고"),
    # --- 모델. 기준선 없이 보고하는 것이 이 프로젝트가 비판하는 실패다. ---
    ("모델을 실패시킴", "src/model.py",
     "def main():", "def main():\n    raise SystemExit(7)", "model.py 가 종료 코드 0"),
    ("같은 해로 학습하고 같은 해로 시험한다(시간 누수)", "src/model.py",
     "TRAIN_YEAR, TEST_YEARS = 2006, (2011, 2016)",
     "TRAIN_YEAR, TEST_YEARS = 2016, (2011, 2016)",
     "모델이 학습 연도보다 **뒤** 코호트로"),
    ("기준선 열을 지우고 모델 점수만 찍는다", "src/model.py",
     '{base:>12.3f} {mod:>8.3f} {mod - base:>+8.3f}',
     '{mod:>12.3f} {mod:>8.3f} {0.0:>+8.3f}',
     "모델 AUC 옆에 기준선"),
    ("보고서가 모델 수치를 옮기지 않고 지어낸다", "src/report.py",
     '            print("  [모델] " + line.strip())',
     '            print("  [모델] " + line.strip().replace("0.6", "0.9"))',
     "보고서의 모델 절이 model.py 출력과"),
    # --- 산술 귀무. 이걸 안 찍으면 발견하지 않은 것을 발견이라 말하게 된다. ---
    ("귀무를 실패시킴", "src/null.py",
     "def main():", "def main():\n    raise SystemExit(7)", "null.py 가 종료 코드 0"),
    # 제목 한 줄만 지우면 표와 설명이 그대로 남는다 — **절이 실제로 사라져야** 시험이 된다.
    ("보고서에서 귀무 절을 통째로 지운다", "src/report.py",
     '_n = _sp2.run([sys.executable, os.path.join(ROOT, "src", "null.py"), "2016"],',
     '_n = _sp2.run([sys.executable, "-c", "pass"],',
     "산술 귀무(p^k)를 기울기"),
    ("귀무를 관측과 같게 만들어 차이를 0으로", "src/null.py",
     "        e = (p ** k) * 100.0", "        e = o",
     "산술 귀무(p^k)를 기울기"),
    ("모델이 다시 전체 spans 를 센다(미래 누수)", "src/model.py",
     "        started = sum(1 for _c, st, _e in v[\"spans\"] if st and st <= f\"{year}-12-31\")",
     "        started = min(len(v[\"spans\"]), 40)",
     "모델 특징이 코호트 연도 이후"),
    ("날짜 파싱을 통째로 꺼서 만료일이 하나도 안 생기게", "src/build.py",
     "        e = iso(p.get(\"EXPIRATION_DATE\"))", "        e = \"\"",
     "특허 만료일이 ISO 형식"),
    ("README 의 검사 개수를 실제와 어긋나게 둔다", "README.md",
     r"re:# \d+ checks, at a denominator", "# 999 checks, at a denominator",
     "README 가 말하는 검사·사보타주 개수가 실제와 같다"),
    ("제출 본문의 수치를 슬쩍 고친다", "submission/devpost.md",
     r"re:\*\*407\*\* \(33\.8 %\)", "**470** (33.8 %)",
     "제출물(devpost·1쪽 PDF)의 수치가 출력과 일치한다"),
    ("1쪽 PDF 원본의 수치를 슬쩍 고친다", "submission/onepager.html",
     r"re:<td class=\"big\">407</td>", '<td class="big">470</td>',
     "제출물(devpost·1쪽 PDF)의 수치가 출력과 일치한다"),
    ("AI 고지의 검사 개수를 옛 값으로 되돌린다", "submission/devpost.md",
     r"re:\d+ checks at a fixed denominator", "25 checks at a fixed denominator",
     "어느 문서도 검사·사보타주 개수를"),
]

# **복원 목록을 손으로 관리하지 않는다.** 겨냥 대상에서 유도한다 —
# 안 그러면 사보타주가 잔해를 남기고, 그 잔해가 '검사 실패'처럼 보인다.
FILES = sorted({f for _d, f, _o, _n, _m in SABS})

bak = tempfile.mkdtemp(prefix="los-sab-")
for f in FILES:
    os.makedirs(os.path.join(bak, os.path.dirname(f)), exist_ok=True)
    shutil.copy2(os.path.join(ROOT, f), os.path.join(bak, f))


def restore():
    for f in FILES:
        shutil.copy2(os.path.join(bak, f), os.path.join(ROOT, f))


atexit.register(restore)
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_a: sys.exit(130))


def digests():
    return {f: hashlib.sha1(open(os.path.join(ROOT, f), "rb").read()).hexdigest() for f in FILES}


START = digests()


def check():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "src", "check.py")],
                       capture_output=True, text=True, timeout=1800)
    m = re.search(r"(\d+)/(\d+) 통과", r.stdout)
    return r.stdout, (int(m.group(1)), int(m.group(2))) if m else (None, None)


only = None
if "--only" in sys.argv:
    only = sys.argv[sys.argv.index("--only") + 1]

print(f"\n  대조군 — 아무것도 망가뜨리지 않았을 때")
print(f"  (도는 동안 {', '.join(FILES)} 를 편집하지 마라 — 복원이 되돌린다)")
out, (p0, d0) = check()
if p0 is None or p0 != d0:
    print(f"    대조군이 통과하지 않는다 ({p0}/{d0}). 사보타주 결과는 의미가 없다.")
    sys.exit(2)
print(f"    {p0}/{d0} 통과. 기준 분모 = {d0}\n")

t0 = time.time()
caught, missed, invalid, shrunk = 0, [], [], []
for desc, f, old, new, must in SABS:
    if only and only not in desc:
        continue
    p = os.path.join(ROOT, f)
    s = io.open(p, encoding="utf-8").read()
    if old.startswith("re:"):
        pat = old[3:]
        if not re.search(pat, s):
            invalid.append(desc)
            print(f"  무효  {desc}\n        정규식이 맞는 곳이 없다: {pat}")
            continue
        io.open(p, "w", encoding="utf-8").write(re.sub(pat, new, s, count=1))
    else:
        if old not in s:
            invalid.append(desc)
            print(f"  무효  {desc}\n        겨냥할 자리를 못 찾았다")
            continue
        io.open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))

    out, (p1, d1) = check()
    restore()
    line = next((l for l in out.splitlines() if must in l), None)
    hit = bool(line) and line.strip().startswith("BAD")
    caught += hit
    if d1 != d0:
        shrunk.append((desc, d1))
    if not hit:
        missed.append(desc)
    print(f"  {'검출' if hit else '놓침'}  {desc}")
    print(f"        {p1}/{d1}" + (f"  <- 분모가 {d0} 에서 변했다!" if d1 != d0 else "")
          + ("" if hit else f"   겨냥한 검사가 초록이다: {must}"))

n = sum(1 for d, *_ in SABS if not only or only in d)
print(f"\n  {n}건 · {time.time() - t0:.0f}초")
print(f"  {caught}/{n} 검출 · 분모 {d0} 고정")
if missed:
    print(f"  놓침 {len(missed)}건 — **검사가 죽어 있거나, 바꾼 것이 동작을 안 바꿨다. 갈라내라.**")
    for m in missed:
        print(f"    · {m}")
if invalid:
    print(f"  무효 {len(invalid)}건 — 코드가 바뀌었는데 이 파일이 안 따라갔다: {invalid}")
if shrunk:
    print(f"  분모가 변한 사보타주 {len(shrunk)}건 — 검사가 조건문 안으로 사라진다: {shrunk}")

end = digests()
clob = [f for f in FILES if START.get(f) != end.get(f)]
if clob:
    print(f"\n  경고: 복원 뒤에도 달라진 파일 {clob} — 도는 동안 편집했나?")
sys.exit(1 if (missed or invalid) else 0)
