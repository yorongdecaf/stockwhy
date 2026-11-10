"""시세 수집 공용 함수 (표준 라이브러리만 사용)."""
import json
import os
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_DIR = os.path.join(ROOT, "data", "prices")


def get(url, headers=None, tries=4, timeout=20):
    """GET 후 bytes 반환. 429/5xx/네트워크 오류는 점점 길게 기다리며 재시도."""
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    h.update(headers or {})
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
        time.sleep(2 * (i + 1))
    raise last


def get_json(url, headers=None, **kw):
    return json.loads(get(url, headers, **kw))


def num(s):
    """'198,000' / '-1.23' / 1234 → float"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).replace(",", "").replace("%", "").strip()
    if s in ("", "N/A", "-"):
        return None
    return float(s)


def pct(x):
    """3.8212 → '+3.82%'"""
    return f"{x:+.2f}%"


def save(name, data):
    os.makedirs(PRICES_DIR, exist_ok=True)
    path = os.path.join(PRICES_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("saved", path)
    return path


def pick_top(rows, key="chg", n=3):
    """등락률 기준 상위/하위 n개. 동률이면 이름순."""
    s = sorted(rows, key=lambda r: (-r[key], r["name"]))
    return s[:n], sorted(rows, key=lambda r: (r[key], r["name"]))[:n]
