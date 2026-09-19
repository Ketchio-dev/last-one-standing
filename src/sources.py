"""출처 한 곳. **모든 스크립트가 여기서만 데이터를 읽는다.**

전부 키도 계정도 없다. 받아 온 원본은 `data/raw/` 에 캐시하고 커밋하지 않는다
(합쳐서 40 MB 가 넘는다). 커밋되는 것은 `data/` 의 **파생 요약**이고,
`fetch_data.py` 가 원본을 언제든 다시 받아 온다.

각 원본의 **가져온 시각과 서버가 말한 Last-Modified 를 같이 기록한다.**
특허 등록부는 분기마다 갱신되는 정적 파일이라, 이걸 안 적어 두면
"오늘 받은 것"과 "오늘자 데이터"를 구분할 수 없다.
"""
import json, os, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
STAMP = os.path.join(RAW, "_fetched.json")

DPD = "https://health-products.canada.ca/api/drug"
SOURCES = {
    # 시판 중인 제품만. status 2 = Marketed.
    "marketed":    f"{DPD}/drugproduct/?lang=en&type=json&status=2",
    # 상태 필터 없이 = **지금까지 존재한 모든 제품**. 시장 이탈을 보려면 이게 필요하다.
    "all_products": f"{DPD}/drugproduct/?lang=en&type=json",
    "ingredients": f"{DPD}/activeingredient/?lang=en&type=json",
    "status":      f"{DPD}/status/?lang=en&type=json",
    "schedule":    f"{DPD}/schedule/?lang=en&type=json",
    "company":     f"{DPD}/company/?lang=en&type=json",
    # 특허 등록부. zip 안에 drugs_e.txt(DIN 열이 있다) + patent-service_e.txt(만료일).
    "patent_zip":  "https://pr-rdb.hc-sc.gc.ca/patent/Patent.zip",
}


def _stamps():
    return json.load(open(STAMP, encoding="utf-8")) if os.path.exists(STAMP) else {}


def fetch(name, refresh=False, quiet=False):
    """원본 파일 경로를 돌려준다. 없으면 받는다."""
    url = SOURCES[name]
    path = os.path.join(RAW, name + (".zip" if url.endswith(".zip") else ".json"))
    os.makedirs(RAW, exist_ok=True)
    if refresh or not os.path.exists(path):
        if not quiet:
            print(f"  받는 중 {name}: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "last-one-standing/0.1"})
        with urllib.request.urlopen(req, timeout=300) as r:
            body = r.read()
            lm = r.headers.get("Last-Modified", "")
        open(path, "wb").write(body)
        st = _stamps()
        st[name] = {"url": url, "bytes": len(body), "last_modified": lm,
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        json.dump(st, open(STAMP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path


def load(name, refresh=False, quiet=False):
    return json.load(open(fetch(name, refresh, quiet), encoding="utf-8"))


def provenance():
    """화면과 문서에 그대로 실을 출처 기록."""
    return _stamps()
