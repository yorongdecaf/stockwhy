"""원고(JSON) → 게시 준비 폴더(posts/<id>/) 생성
- 카드 8장(인스타는 JPEG만 받으므로 .jpg 변환), 무음 릴스, 캡션, post.json
사용법: python3 generator/make_post.py data/us_2026-10-30.json
"""
import json, sys, pathlib, shutil
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cards import render_cards
from reel_carousel import make as make_reel
from brand import HANDLE

ROOT = pathlib.Path(__file__).resolve().parent.parent

HASHTAGS = {
    "us": "#미국주식 #미장 #주식 #나스닥 #SP500 #주가 #급등주 #급락주 #경제뉴스 #재테크 #주식공부 #스톡와이",
    "kr": "#국내주식 #국장 #주식 #코스피 #코스닥 #주가 #급등주 #급락주 #경제뉴스 #재테크 #주식공부 #스톡와이",
}

def short_why(s):
    return s["why"][0].split(", ")[0]   # "1,150억" 같은 숫자 쉼표는 자르지 않음

def caption(d):
    head = d["cover"]["title"].replace("\n", " ")
    up = "\n".join(f"{i+1}. {s['name']} {s['chg']} : {short_why(s)}" for i, s in enumerate(d["up"]))
    dn = "\n".join(f"{i+1}. {s['name']} {s['chg']} : {short_why(s)}" for i, s in enumerate(d["down"]))
    names = " ".join("#" + s["name"].replace(" ", "") for s in d["up"] + d["down"])
    return (f"{head} 📈📉\n\n"
            f"{d['date']} · {d['cover']['sub']}\n\n"
            f"▲ 상승 TOP3\n{up}\n\n▼ 하락 TOP3\n{dn}\n\n"
            f"💡 한 줄 정리\n{d['takeaway']}\n\n"
            f"📌 장 마감 후 오른 이유·내린 이유, 매일 정리합니다\n"
            f"저장해두고 팔로우하세요 👉 {HANDLE}\n\n"
            f"※ 본 게시물은 정보 제공 목적이며 특정 종목의 매수·매도를 권유하지 않습니다.\n"
            f"※ {d['universe']}\n\n"
            f"{HASHTAGS[d['market']]} {names}")

def threads_text(d):
    """스레드는 본문 500자 제한 → 짧은 버전"""
    head = d["cover"]["title"].replace("\n", " ")
    up = "\n".join(f"▲ {s['name']} {s['chg']}" for s in d["up"])
    dn = "\n".join(f"▼ {s['name']} {s['chg']}" for s in d["down"])
    t = (f"{head}\n\n{d['date']} · {d['cover']['sub']}\n\n{up}\n{dn}\n\n"
         f"💡 {d['takeaway']}\n\n오른 이유·내린 이유는 카드에서 👉\n"
         f"※ 정보 제공 목적, 투자 권유 아님")
    return t[:500]

def main(data_path):
    d = json.loads(pathlib.Path(data_path).read_text())
    pid = pathlib.Path(data_path).stem                      # 예: us_2026-10-30
    out = ROOT / "posts" / pid
    work = ROOT / "build" / pid
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True); work.mkdir(parents=True, exist_ok=True)

    render_cards(d, work)
    make_reel(work)
    cards = []
    for p in sorted(work.glob("card_*.png")):
        jp = out / (p.stem + ".jpg")
        Image.open(p).convert("RGB").save(jp, "JPEG", quality=92, optimize=True)
        cards.append(jp.name)
    shutil.copy(work / "reel.mp4", out / "reel.mp4")
    cap = caption(d)
    if "caption" in d: cap = d["caption"]                  # 원고에 직접 쓴 캡션이 있으면 우선
    (out / "caption.txt").write_text(cap)
    (out / "threads.txt").write_text(threads_text(d))
    (out / "post.json").write_text(json.dumps({
        "id": pid, "cards": cards, "reel": "reel.mp4",
        "reel_share_to_feed": False,                       # 피드엔 카드뉴스만, 릴스는 릴스 탭에만
        "publish": True
    }, ensure_ascii=False, indent=2))
    print("post ready:", out)

if __name__ == "__main__":
    main(sys.argv[1])
