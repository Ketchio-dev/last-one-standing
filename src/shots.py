"""앱 화면을 상태별로 찍는다. 영상이 "사용자가 조작하는 모습"을 보여야 하기 때문이다.

    python3 src/shots.py

헤드리스 크롬은 클릭을 못 한다. 그래서 `index.html` 을 복사하고 **끝에 작은 스크립트를
덧붙여** 컨트롤을 미리 맞춘 뒤 찍는다. 원본은 건드리지 않는다.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "web", "index.html")
FIG = os.path.join(ROOT, "figures")
CHROME = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1243/"
    "chrome-headless-shell-mac-arm64/chrome-headless-shell")

# (파일명, 설명, 페이지에서 미리 실행할 스크립트, 창 높이)
SHOTS = [
    ("01-default", "기본 — 처방전용 + 특허 없음 + 한때 둘 이상", "", 1180),
    ("02-otc", "'처방전용'을 끄면 목록 맨 위가 OTC 로 바뀐다",
     "document.getElementById('rx').checked=false;"
     "document.getElementById('rx').dispatchEvent(new Event('input'));", 1180),
    ("03-search", "약 이름으로 찾기 — lovastatin",
     "const q=document.getElementById('q');q.value='lovastatin';"
     "q.dispatchEvent(new Event('input'));"
     "document.querySelector('#rows tr').click();", 1180),
    # 헤드리스 크롬은 **뷰포트 맨 위**를 찍는다. scrollIntoView 로는 안 잡힌다 —
    # 앞 카드를 지워 보고 싶은 것을 맨 위로 올린다.
    ("04-cohorts", "코호트 — 공급자 수가 소멸을 예측하는가",
     "const keep=document.getElementById('cohorts').closest('.card');"
     "[...document.querySelectorAll('main > .card')].forEach(c=>{if(c!==keep)c.remove();});"
     "document.querySelector('h1').textContent='Does supplier count predict the medicine disappearing?';", 760),
]


def main():
    if not os.path.exists(CHROME):
        sys.exit(f"헤드리스 크롬을 못 찾았다: {CHROME}")
    if not os.path.exists(IDX):
        sys.exit("web/index.html 이 없다 — python3 src/export_web.py")
    os.makedirs(FIG, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="los-shots-")
    made = []
    for name, why, js, h in SHOTS:
        path = os.path.join(tmp, name + ".html")
        body = open(IDX, encoding="utf-8").read()
        if js:
            # 페이지 스크립트가 다 돈 뒤에 실행되도록 맨 끝에 붙인다.
            body += f"\n<script>setTimeout(()=>{{{js}}},60);</script>\n"
        open(path, "w", encoding="utf-8").write(body)
        out = os.path.join(FIG, name + ".png")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size=1240,{h}", f"--screenshot={out}",
                        "--virtual-time-budget=8000", "file://" + path],
                       capture_output=True, timeout=120)
        ok = os.path.exists(out) and os.path.getsize(out) > 20000
        made.append((name, ok, why))
        print(f"  {'✓' if ok else '✗'} figures/{name}.png  — {why}")
    shutil.rmtree(tmp, ignore_errors=True)
    bad = [n for n, ok, _ in made if not ok]
    if bad:
        sys.exit(f"찍히지 않은 화면: {bad}")


if __name__ == "__main__":
    main()
