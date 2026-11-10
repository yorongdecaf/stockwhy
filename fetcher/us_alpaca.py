"""미장 시세 수집: S&P 500 구성 종목 정규장 종가 등락률 → data/prices/us_<날짜>.json

1순위: Alpaca Market Data (SIP 일봉) — GitHub Secrets ALPACA_KEY_ID / ALPACA_SECRET_KEY 필요
대체:  야후 파이낸스 차트 API (키 없을 때·Alpaca 실패 시)
지수:  네이버 해외지수 API(.INX, .IXIC) → 실패 시 야후(^GSPC, ^IXIC)

사용: python fetcher/us_alpaca.py [--date YYYY-MM-DD(미국 현지 거래일)] [--source alpaca|yahoo]
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

from common import ROOT, get, get_json, num, pct, pick_top, save

NY = ZoneInfo("America/New_York")
SP500_CACHE = os.path.join(ROOT, "data", "sp500.json")


# ---------- 구성 종목 ----------
def sp500():
    """위키백과 구성 종목표 → [{sym, name, sector}] (실패 시 저장된 목록 사용)"""
    try:
        h = get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies").decode()
        i = h.find('id="constituents"')
        t = h[i:h.find("</table>", i)]
        out = []
        for row in re.split(r"<tr[^>]*>", t)[2:]:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            if len(cells) < 3:
                continue
            txt = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in cells]
            out.append({"sym": txt[0], "name": txt[1], "sector": txt[2]})
        if len(out) < 490:
            raise ValueError(f"구성 종목 수 이상: {len(out)}")
        with open(SP500_CACHE, "w", encoding="utf-8") as f:
            json.dump({"updated": dt.date.today().isoformat(), "list": out}, f, ensure_ascii=False, indent=0)
        return out, "wikipedia"
    except Exception as e:
        print("위키백과 목록 실패, 저장된 목록 사용:", e)
        with open(SP500_CACHE, encoding="utf-8") as f:
            c = json.load(f)
        return c["list"], f"cache({c['updated']})"


# ---------- Alpaca ----------
def alpaca_bars(syms, date):
    key, sec = os.environ.get("ALPACA_KEY_ID"), os.environ.get("ALPACA_SECRET_KEY")
    if not (key and sec):
        raise RuntimeError("ALPACA 키 없음")
    hdr = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}
    d = dt.date.fromisoformat(date)
    start = (d - dt.timedelta(days=10)).isoformat()
    # 무료 플랜은 최근 15분 SIP 데이터를 못 받음 → end를 16분 전으로
    end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    bars = {}
    for i in range(0, len(syms), 200):
        chunk = syms[i:i + 200]
        token = None
        while True:
            q = {"symbols": ",".join(chunk), "timeframe": "1Day", "start": start, "end": end,
                 "feed": "sip", "adjustment": "split", "limit": 10000}
            if token:
                q["page_token"] = token
            r = get_json("https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(q), hdr)
            for s, L in (r.get("bars") or {}).items():
                bars.setdefault(s, []).extend(L)
            token = r.get("next_page_token")
            if not token:
                break
    out = {}
    for s, L in bars.items():
        L.sort(key=lambda b: b["t"])
        ds = [dt.datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(NY).date().isoformat() for b in L]
        if date in ds:
            k = ds.index(date)
            if k > 0:
                out[s] = (L[k]["c"], L[k - 1]["c"])
    return out


# ---------- Yahoo ----------
def yahoo_one(sym, date):
    ys = sym.replace(".", "-")
    try:
        r = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ys)}?range=1mo&interval=1d",
                     tries=3)["chart"]["result"][0]
    except Exception:
        return sym, None
    ts, cl = r.get("timestamp") or [], r["indicators"]["quote"][0].get("close") or []
    ds = [dt.datetime.fromtimestamp(t, NY).date().isoformat() for t in ts]
    pairs = [(d_, c) for d_, c in zip(ds, cl) if c is not None]
    for k, (d_, c) in enumerate(pairs):
        if d_ == date and k > 0:
            return sym, (c, pairs[k - 1][1])
    return sym, None


def yahoo_bars(syms, date):
    with ThreadPoolExecutor(8) as ex:
        return {s: v for s, v in ex.map(lambda s: yahoo_one(s, date), syms) if v}


# ---------- 지수 ----------
def index_info(naver_code, yahoo_code, date):
    try:
        r = get_json(f"https://api.stock.naver.com/index/{naver_code}/basic")
        if r["localTradedAt"][:10] == date:
            c = num(r["fluctuationsRatio"])
            return {"close": num(r["closePrice"]), "chg": c, "chg_str": pct(c), "src": "naver"}
    except Exception as e:
        print("네이버 지수 실패", naver_code, e)
    v = yahoo_one(yahoo_code, date)[1]
    if v:
        c = (v[0] / v[1] - 1) * 100
        return {"close": round(v[0], 2), "chg": round(c, 2), "chg_str": pct(c), "src": "yahoo"}
    return None


def default_date():
    now = dt.datetime.now(NY)
    d = now.date() if now.hour >= 17 or (now.hour == 16 and now.minute >= 20) else now.date() - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=default_date())
    ap.add_argument("--source", choices=["alpaca", "yahoo"], default=None)
    a = ap.parse_args()
    date = a.date
    name = f"us_{date}.json"
    fetched_at = dt.datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")

    members, members_src = sp500()
    syms = [m["sym"] for m in members]

    src, bars = None, {}
    if a.source != "yahoo":
        try:
            bars = alpaca_bars(syms + ["SPY"], date)
            src = "alpaca (SIP 일봉, 정규장 종가)"
        except Exception as e:
            print("Alpaca 실패 → 야후로 대체:", e)
    if len(bars) < 400:
        bars = yahoo_bars(syms + ["SPY"], date)
        src = "yahoo chart API (일봉 종가)"

    if "SPY" not in bars and len(bars) < 50:
        save(name, {"market": "us", "date": date, "status": "closed", "source": src,
                    "fetched_at": fetched_at, "note": "해당 날짜 일봉 없음 → 휴장(또는 아직 미마감)"})
        print("휴장/데이터 없음:", date)
        return

    rows, missing = [], []
    for m in members:
        v = bars.get(m["sym"])
        if not v or not v[1]:
            missing.append(m["sym"])
            continue
        c = (v[0] / v[1] - 1) * 100
        rows.append({"name": m["name"], "code": m["sym"], "sector": m["sector"],
                     "close": round(v[0], 4), "prev_close": round(v[1], 4),
                     "chg": round(c, 4), "chg_str": pct(c)})
    if len(rows) < 480:
        sys.exit(f"종목 시세가 너무 적음 ({len(rows)}/{len(members)}) — 저장하지 않음")

    up, down = pick_top(rows)

    # 상위·하위 6개는 다른 출처(야후)로 한 번 더 대조
    check = {}
    if src.startswith("alpaca"):
        for r in up + down:
            y = yahoo_one(r["code"], date)[1]
            if y:
                yc = (y[0] / y[1] - 1) * 100
                check[r["code"]] = {"yahoo_chg": pct(yc), "diff_pp": round(abs(yc - r["chg"]), 3)}

    spx = index_info(".INX", "^GSPC", date)
    ixic = index_info(".IXIC", "^IXIC", date)
    rising = sum(1 for r in rows if r["chg"] > 0)
    out = {
        "market": "us", "date": date, "status": "ok", "source": src,
        "fetched_at": fetched_at,
        "universe": f"S&P 500 구성 종목 {len(members)}개 ({members_src})",
        "index": {"SPX": spx, "IXIC": ixic},
        "cover_sub": f"S&P 500 {spx['chg_str'] if spx else '?'} · 나스닥 {ixic['chg_str'] if ixic else '?'}",
        "rising_count": rising,
        "up_label": "선방" if rising < 3 else "상승",
        "up_top3": up, "down_top3": down,
        "cross_check": check,
        "missing": missing,
        "all": sorted(rows, key=lambda r: -r["chg"]),
    }
    save(name, out)
    print(src, "|", out["cover_sub"])
    for t, L in (("UP", up), ("DOWN", down)):
        print(t, " / ".join(f"{r['code']} {r['chg_str']}" for r in L))
    if check:
        print("대조:", check)


if __name__ == "__main__":
    main()
