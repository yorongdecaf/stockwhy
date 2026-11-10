"""국장 시세 수집 → data/prices/kr_<날짜>.json

- 종목 범위·지수: 네이버 증권 모바일 API (코스피 시총 순위, 코스피·코스닥 일별 지수)
- 종목 등락률: 야후 파이낸스 <코드>.KS 일봉 = KRX 정규장 종가
  ※ 네이버 종목 시세(일별·실시간 모두)는 넥스트레이드(NXT) 통합가라 쓰지 않음.
    11/06 검증: NAVER 정규장 +2.87% / 네이버 +2.00% / 야후 +2.87%
- 네이버 통합가는 참고용(naver_chg)으로만 같이 저장

사용: python fetcher/kr.py [--date YYYY-MM-DD]
"""
import argparse
import datetime as dt
import sys
import time
from zoneinfo import ZoneInfo

from common import get_json, num, pct, pick_top, save

NV = "https://m.stock.naver.com/api"
KST = ZoneInfo("Asia/Seoul")
UNIVERSE = 30


def naver_index(code, date):
    rows = get_json(f"{NV}/index/{code}/price?pageSize=5&page=1")
    for r in rows:
        if r["localTradedAt"][:10] == date:
            c = num(r["fluctuationsRatio"])
            return {"close": num(r["closePrice"]), "chg": c, "chg_str": pct(c)}
    return None


def yahoo_krx(code, date):
    """(종가, 전일 종가, 마지막 체결 시각) — 해당 날짜 일봉이 없으면 None"""
    r = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.KS?range=1mo&interval=1d",
                 tries=4)["chart"]["result"][0]
    ts, cl = r.get("timestamp") or [], r["indicators"]["quote"][0].get("close") or []
    pairs = [(dt.datetime.fromtimestamp(t, KST).date().isoformat(), c) for t, c in zip(ts, cl) if c]
    for k, (d, c) in enumerate(pairs):
        if d == date and k > 0:
            return c, pairs[k - 1][1], r["meta"].get("regularMarketTime")
    return None


def main():
    today = dt.datetime.now(KST).date().isoformat()
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=today)
    a = ap.parse_args()
    date = a.date
    name = f"kr_{date}.json"
    fetched_at = dt.datetime.now(KST).isoformat(timespec="seconds")

    # 1) 마감 시각 확인 (야후 국내 시세는 약 20분 지연 → 15:50 이후 확정)
    close_ts = dt.datetime.fromisoformat(f"{date}T15:50:00+09:00")
    if dt.datetime.now(KST) < close_ts:
        sys.exit("아직 종가 확정 전입니다. 15:50(KST) 이후 다시 실행하세요.")

    # 2) 휴장 확인 (코스피 지수 일별 시세)
    kospi = naver_index("KOSPI", date)
    if not kospi:
        save(name, {"market": "kr", "date": date, "status": "closed", "fetched_at": fetched_at,
                    "note": "해당 날짜 코스피 일별 시세 없음 → 휴장"})
        print("휴장:", date)
        return
    kosdaq = naver_index("KOSDAQ", date)

    # 3) 시총 상위 보통주 30 (ETF·우선주 제외, 수집 시점 시총 순)
    lst = get_json(f"{NV}/stocks/marketValue/KOSPI?page=1&pageSize=80")["stocks"]
    universe = [s for s in lst if s.get("stockEndType") == "stock" and s["itemCode"].endswith("0")][:UNIVERSE]

    # 4) 종목별 KRX 정규장 종가 (야후)
    rows, missing = [], []
    for rank, s in enumerate(universe, 1):
        code = s["itemCode"]
        try:
            y = yahoo_krx(code, date)
        except Exception as e:
            y = None
            print("야후 오류", code, e)
        time.sleep(0.2)
        if not y:
            missing.append({"code": code, "name": s["stockName"]})
            continue
        close, prev, mt = y
        if date == today and mt and mt < close_ts.timestamp() - 20 * 60:
            sys.exit(f"{s['stockName']} 마지막 체결이 15:30 이전 → 종가 미확정, 잠시 후 재실행")
        c = (close / prev - 1) * 100
        rows.append({
            "rank": rank, "name": s["stockName"], "code": code,
            "close": close, "prev_close": prev,
            "chg": round(c, 4), "chg_str": pct(c),
            "naver_chg": (pct(num(s["fluctuationsRatio"])) if date == today else None),  # NXT 통합가 참고용
            "mcap_eok": num(s["marketValue"]),
        })

    if len(rows) < UNIVERSE - 2:
        sys.exit(f"종목 시세가 너무 적음 ({len(rows)}/{UNIVERSE}) — 저장하지 않음")

    up, down = pick_top(rows)
    rising = sum(1 for r in rows if r["chg"] > 0)
    out = {
        "market": "kr", "date": date, "status": "ok",
        "source": "종목: 야후 .KS 일봉(KRX 정규장 종가) / 범위·지수: 네이버 증권",
        "fetched_at": fetched_at,
        "universe": f"코스피 시가총액 상위 {UNIVERSE} 보통주 (ETF·우선주 제외, 수집 시점 시총 순)",
        "index": {"KOSPI": kospi, "KOSDAQ": kosdaq},
        "cover_sub": f"코스피 {kospi['chg_str']} · 코스닥 {kosdaq['chg_str'] if kosdaq else '?'}",
        "rising_count": rising,
        "up_label": "선방" if rising < 3 else "상승",
        "up_top3": up, "down_top3": down,
        "missing": missing,
        "all": sorted(rows, key=lambda r: -r["chg"]),
    }
    save(name, out)
    print(out["cover_sub"])
    for t, L in (("UP", up), ("DOWN", down)):
        print(t, " / ".join(f"{r['name']} {r['chg_str']}" for r in L))


if __name__ == "__main__":
    main()
