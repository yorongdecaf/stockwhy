"""국장 시세 수집: 네이버 증권 모바일 API
코스피 시가총액 상위 30 보통주(ETF·우선주 제외)의 정규장 종가 등락률 → data/prices/kr_<날짜>.json

사용: python fetcher/kr_naver.py [--date YYYY-MM-DD] [--force]
- 종목별 등락률은 일별 시세(/api/stock/<코드>/price, KRX 정규장 종가)에서 가져옴.
  넥스트레이드(NXT) 애프터마켓 가격은 쓰지 않음.
- 그날 지수 일별 시세가 없으면 휴장으로 보고 status="closed"로 저장.
"""
import argparse
import datetime as dt
import sys
import time

from common import get_json, num, pct, pick_top, save

API = "https://m.stock.naver.com/api"
UNIVERSE = 30


def daily_row(path, date):
    """일별 시세에서 date 행과 그 전 행을 반환"""
    rows = get_json(f"{API}/{path}/price?pageSize=5&page=1")
    for i, r in enumerate(rows):
        if r["localTradedAt"][:10] == date:
            return r, (rows[i + 1] if i + 1 < len(rows) else None)
    return None, None


def index_info(code, date):
    r, prev = daily_row(f"index/{code}", date)
    if not r:
        return None
    return {"close": num(r["closePrice"]), "chg": num(r["fluctuationsRatio"]),
            "chg_str": pct(num(r["fluctuationsRatio"]))}


def main():
    ap = argparse.ArgumentParser()
    kst_today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    ap.add_argument("--date", default=kst_today)
    ap.add_argument("--force", action="store_true", help="장중이어도 저장(점검용)")
    a = ap.parse_args()
    date = a.date
    name = f"kr_{date}.json"
    fetched_at = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")

    # 1) 장 상태·휴장 확인
    status = get_json(f"{API}/index/KOSPI/basic").get("marketStatus")
    if date == kst_today and status == "OPEN" and not a.force:
        sys.exit(f"아직 장중입니다 (marketStatus=OPEN). 15:30 이후 다시 실행하세요.")
    kospi = index_info("KOSPI", date)
    if not kospi:
        save(name, {"market": "kr", "date": date, "status": "closed",
                    "source": "naver", "fetched_at": fetched_at,
                    "note": "해당 날짜 코스피 일별 시세 없음 → 휴장"})
        print("휴장:", date)
        return
    kosdaq = index_info("KOSDAQ", date)

    # 2) 시총 상위 보통주 30
    lst = get_json(f"{API}/stocks/marketValue/KOSPI?page=1&pageSize=80")["stocks"]
    universe = [s for s in lst
                if s.get("stockEndType") == "stock" and s["itemCode"].endswith("0")][:UNIVERSE]

    # 3) 종목별 정규장 종가
    rows, missing = [], []
    for rank, s in enumerate(universe, 1):
        code = s["itemCode"]
        try:
            r, prev = daily_row(f"stock/{code}", date)
        except Exception as e:  # 한 종목 오류로 전체가 멈추지 않게
            r, prev = None, None
            print("오류", code, e)
        time.sleep(0.15)
        if not r:
            missing.append({"code": code, "name": s["stockName"]})
            continue
        close, chg = num(r["closePrice"]), num(r["fluctuationsRatio"])
        prev_close = close - num(r["compareToPreviousClosePrice"])
        rows.append({
            "rank": rank, "name": s["stockName"], "code": code,
            "close": close, "prev_close": prev_close,
            "chg": chg, "chg_str": pct(chg),
            "mcap_eok": num(s["marketValue"]),  # 억 원
        })

    if len(rows) < UNIVERSE - 2:
        sys.exit(f"종목 시세가 너무 적음 ({len(rows)}/{UNIVERSE}) — 저장하지 않음")

    up, down = pick_top(rows)
    rising = sum(1 for r in rows if r["chg"] > 0)
    out = {
        "market": "kr", "date": date, "status": "ok",
        "source": "naver m.stock API (KRX 정규장 일별 종가)",
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
