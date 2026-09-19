"""원본을 전부 받아 온다. 키도 계정도 없다.

    python3 src/fetch_data.py            # 캐시에 없는 것만
    python3 src/fetch_data.py --refresh  # 전부 다시
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import SOURCES, fetch, provenance

refresh = "--refresh" in sys.argv
for name in SOURCES:
    fetch(name, refresh)
print()
for name, s in provenance().items():
    lm = s["last_modified"] or "(서버가 안 알려줌)"
    print(f"  {name:<14} {s['bytes']:>10,} bytes · Last-Modified {lm}")
print("\n  Last-Modified 를 화면에도 싣는다 — '오늘 받은 것'과 '오늘자 데이터'는 다르다.")
