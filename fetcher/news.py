"""뉴스·공식 발표 수집 → data/news/<KST 날짜>.json

공식 원문(연준·한국은행·DART)과 주요 언론 RSS에서 제목·링크·시각만 모은다.
기사 본문은 저장하지 않는다 (저작권). 실제 콘텐츠를 만들 때 링크를 열어 원문을 확인한다.
같은 날 여러 번 돌면 기존 파일에 합치고 링크 기준으로 중복을 없앤다.
실패한 출처는 errors 에 남기고 나머지는 계속 진행한다.
"""
import json, os, re, sys, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; stockwhy-news/1.0; +https://github.com/yorongdecaf/stockwhy)"

# (id, 표시 이름, 등급, 분야, URL)  등급: official=공식 원문, press=주요 언론
FEEDS = [
    ("fed_press",    "미국 연준 보도자료",  "official", "us_policy", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("fed_speech",   "미국 연준 연설",      "official", "us_policy", "https://www.federalreserve.gov/feeds/speeches.xml"),
    ("bls",          "미국 노동통계국",     "official", "us_macro",  "https://www.bls.gov/feed/bls_latest.rss"),
    ("yna_economy",  "연합뉴스 경제",       "press",    "kr",        "https://www.yna.co.kr/rss/economy.xml"),
    ("yna_market",   "연합뉴스 마켓+",      "press",    "kr",        "https://www.yna.co.kr/rss/market.xml"),
    ("yna_world",    "연합뉴스 국제",       "press",    "world",     "https://www.yna.co.kr/rss/international.xml"),
    ("hk_finance",   "한국경제 증권",       "press",    "kr",        "https://www.hankyung.com/feed/finance"),
    ("hk_economy",   "한국경제 경제",       "press",    "kr",        "https://www.hankyung.com/feed/economy"),
    ("mk_stock",     "매일경제 증권",       "press",    "kr",        "https://www.mk.co.kr/rss/50200011/"),
    ("cnbc_economy", "CNBC Economy",        "press",    "us",        "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    ("cnbc_finance", "CNBC Finance",        "press",    "us",        "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
]

# 한국은행 보도자료 (RSS 주소가 바뀌는 일이 있어 후보 여러 개를 차례로 시도)
BOK_CANDIDATES = [
    "https://www.bok.or.kr/portal/bbs/B0000501/news.rss?menuNo=201264",
    "https://www.bok.or.kr/portal/bbs/B0000338/news.rss?menuNo=200761",
]


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def to_kst(s):
    if not s:
        return ""
    try:
        dt = parsedate_to_datetime(s)
    except Exception:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return s
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).isoformat(timespec="minutes")


def parse_feed(raw):
    root = ET.fromstring(raw)
    out = []
    # RSS 2.0
    for it in root.iter("item"):
        out.append({
            "title": clean(it.findtext("title")),
            "link": (it.findtext("link") or "").strip(),
            "published": to_kst(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
        })
    # Atom
    ns = "{http://www.w3.org/2005/Atom}"
    for e in root.iter(ns + "entry"):
        link = e.find(ns + "link")
        out.append({
            "title": clean(e.findtext(ns + "title")),
            "link": link.get("href") if link is not None else "",
            "published": to_kst(e.findtext(ns + "updated") or e.findtext(ns + "published")),
        })
    return [x for x in out if x["title"] and x["link"]]


def fetch_dart(key, today):
    """유가증권 상장사 당일 주요 공시 중 코스피 시총 상위 30 종목만"""
    top30 = set()
    pf = sorted((ROOT / "data" / "prices").glob("kr_*.json"))
    if pf:
        try:
            top30 = {s["name"] for s in json.loads(pf[-1].read_text())["all"]}
        except Exception:
            pass
    d = today.strftime("%Y%m%d")
    items, page = [], 1
    while page <= 5:
        q = urllib.parse.urlencode({"crtfc_key": key, "bgn_de": d, "end_de": d, "corp_cls": "Y",
                                    "page_no": page, "page_count": 100})
        js = json.loads(get("https://opendart.fss.or.kr/api/list.json?" + q))
        if js.get("status") != "000":
            if js.get("status") == "013":  # 조회된 데이터 없음
                break
            raise RuntimeError(f"DART {js.get('status')}: {js.get('message')}")
        for r in js.get("list", []):
            if top30 and r["corp_name"] not in top30:
                continue
            items.append({
                "title": f"[{r['corp_name']}] {clean(r['report_nm'])}",
                "link": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={r['rcept_no']}",
                "published": f"{r['rcept_dt'][:4]}-{r['rcept_dt'][4:6]}-{r['rcept_dt'][6:]}",
            })
        if page >= js.get("total_page", 1):
            break
        page += 1
    return items


def main():
    now = datetime.now(KST)
    today = now.date()
    path = ROOT / "data" / "news" / f"{today.isoformat()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text()) if path.exists() else {"date": today.isoformat(), "items": []}
    seen = {x["link"] for x in data["items"]}
    errors, counts = {}, {}

    def add(fid, name, tier, cat, items):
        n = 0
        for x in items:
            if x["link"] in seen:
                continue
            seen.add(x["link"])
            data["items"].append({**x, "source": name, "source_id": fid, "tier": tier, "category": cat})
            n += 1
        counts[fid] = n

    for fid, name, tier, cat, url in FEEDS:
        try:
            add(fid, name, tier, cat, parse_feed(get(url))[:40])
        except Exception as e:
            errors[fid] = f"{type(e).__name__}: {e}"[:200]

    for url in BOK_CANDIDATES:
        try:
            add("bok", "한국은행 보도자료", "official", "kr_policy", parse_feed(get(url))[:30])
            errors.pop("bok", None)
            break
        except Exception as e:
            errors["bok"] = f"{type(e).__name__}: {e}"[:200]

    key = os.environ.get("DART_API_KEY", "").strip()
    if key:
        try:
            add("dart", "DART 공시", "official", "kr_company", fetch_dart(key, today))
        except Exception as e:
            errors["dart"] = f"{type(e).__name__}: {e}"[:200]
    else:
        errors["dart"] = "DART_API_KEY 없음 (GitHub Secrets에 등록하면 수집)"

    data["items"].sort(key=lambda x: x.get("published", ""), reverse=True)
    data["updated_at"] = now.isoformat(timespec="minutes")
    data["last_run"] = {"added": counts, "errors": errors}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"저장: {path.relative_to(ROOT)} · 총 {len(data['items'])}건")
    for k, v in counts.items():
        print(f"  + {k}: {v}건")
    for k, v in errors.items():
        print(f"  ⚠ {k}: {v}")
    if not counts:
        sys.exit("모든 출처 실패")


if __name__ == "__main__":
    main()
