"""'경제용어, 왜?' 카드뉴스 (1080x1350, 7장)
원고: data/term_<YYYY-MM-DD>.json  → posts/term_<YYYY-MM-DD>/
사용법: python3 generator/term.py data/term_2026-11-03.json
"""
import json, sys, html, pathlib, shutil
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from brand import *
from reel_carousel import make as make_reel

ROOT = pathlib.Path(__file__).resolve().parent.parent
def e(s): return html.escape(s).replace("\n", "<br>")

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1350px;overflow:hidden;word-break:keep-all}}
body{{font-family:{FONT};background:{PAPER};color:{INK};padding:84px 92px 0;display:flex;flex-direction:column;position:relative}}
.hl{{background:linear-gradient(transparent 60%,{YELLOW} 60%)}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.chip{{font-size:30px;font-weight:900;padding:12px 26px;border-radius:999px;background:{INK};color:{YELLOW}}}
.no{{font-size:28px;font-weight:700;color:{GRAY}}}
.foot{{position:absolute;left:92px;right:92px;bottom:60px;display:flex;justify-content:space-between;align-items:center;font-size:24px;color:#A0A0A0;font-weight:700}}
.ctitle{{font-size:92px;font-weight:900;line-height:1.22;letter-spacing:-3px;margin-top:auto}}
.term{{display:inline-flex;align-items:center;gap:18px;margin-top:48px;font-size:46px;font-weight:900;border:4px solid {INK};border-radius:20px;padding:16px 30px;align-self:flex-start}}
.term b{{background:{YELLOW};border-radius:50%;width:56px;height:56px;display:flex;align-items:center;justify-content:center;font-size:40px}}
.csub{{font-size:38px;font-weight:700;color:#555;margin:36px 0 170px}}
.lbl{{font-size:32px;font-weight:900;color:{GRAY};margin-top:64px}}
h2{{font-size:76px;font-weight:900;line-height:1.28;letter-spacing:-2px;margin-top:22px}}
.big{{font-size:64px;font-weight:900;line-height:1.38;letter-spacing:-2px;margin-top:40px}}
p{{font-size:42px;line-height:1.6;color:#2A2A2A;margin-top:36px}}
.box{{margin-top:44px;background:{INK};color:#fff;border-radius:24px;padding:38px 44px;font-size:38px;line-height:1.55}}
.box em{{font-style:normal;color:{YELLOW};font-weight:900}}
.row{{display:flex;gap:26px;align-items:flex-start;padding:28px 0;border-bottom:3px solid #E4DFD3}}
.row b{{flex:none;width:58px;height:58px;border-radius:50%;background:{YELLOW};display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:900}}
.row div{{font-size:42px;font-weight:700;line-height:1.4}}
.row small{{display:block;font-size:32px;font-weight:500;color:#666;margin-top:6px}}
.pz{{display:flex;justify-content:space-around;align-items:center;margin-top:50px}}
.pz figure{{text-align:center}}
.pz figcaption{{font-size:36px;font-weight:900;margin-top:18px}}
.pz figcaption span{{display:block;font-size:30px;font-weight:700;color:#666;margin-top:4px}}
.arrow{{font-size:80px;font-weight:900;color:{GRAY}}}
.tl{{margin-top:34px;border-left:6px solid {INK};padding-left:40px}}
.tl div{{position:relative;padding:14px 0}}
.tl div:before{{content:"";position:absolute;left:-55px;top:24px;width:24px;height:24px;border-radius:50%;background:{YELLOW};border:5px solid {INK}}}
.tl small{{display:block;font-size:28px;font-weight:900;color:{GRAY}}}
.tl strong{{display:block;font-size:44px;font-weight:900;letter-spacing:-1px;margin-top:4px}}
.tl span{{display:block;font-size:32px;font-weight:500;color:#555;margin-top:4px;line-height:1.4}}
.stat{{display:flex;gap:24px;margin-top:44px}}
.stat div{{flex:1;background:#fff;border:3px solid {INK};border-radius:22px;padding:26px 12px;text-align:center}}
.stat strong{{display:block;font-size:52px;font-weight:900;letter-spacing:-2px;white-space:nowrap}}
.stat span{{display:block;font-size:27px;font-weight:700;color:#555;margin-top:6px}}
"""

def pizza(slices, mine, size=300):
    """slices 조각 중 mine 조각을 노란색으로 칠한 원형 피자"""
    import math
    cx = cy = size / 2; r = size / 2 - 6; out = []
    for i in range(slices):
        a0 = -math.pi / 2 + 2 * math.pi * i / slices
        a1 = -math.pi / 2 + 2 * math.pi * (i + 1) / slices
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        fill = YELLOW if i < mine else "#FFFFFF"
        out.append(f'<path d="M{cx},{cy} L{x0:.1f},{y0:.1f} A{r},{r} 0 0,1 {x1:.1f},{y1:.1f} Z" '
                   f'fill="{fill}" stroke="{INK}" stroke-width="5"/>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{"".join(out)}</svg>'

def foot(n, total):
    return f'<div class="foot"><span>{logo(24)}&nbsp;&nbsp;<span style="font-size:22px">{HANDLE}</span></span><span>{n}/{total}</span></div>'

def head(d):
    return f'<div class="top"><span class="chip">경제용어, 왜? #{d["no"]:03d}</span><span class="no">{e(d["date"])}</span></div>'

def pages(d):
    T = 7
    P = []
    # 1 표지
    P.append(f"""{head(d)}
      <div class="ctitle">{e(d['cover']['title'])}</div>
      <div class="term"><b>?</b>{e(d['term'])}</div>
      <div class="csub">{e(d['cover']['sub'])}</div>
      <div class="foot"><span>{HANDLE}</span><span>넘겨보기 →</span></div>""")
    # 2 한 줄 정의
    P.append(f"""{head(d)}<div class="lbl">한 줄로 말하면</div>
      <div class="big">{d['define_html']}</div>
      <p>{e(d['define_sub'])}</p>{foot(2, T)}""")
    # 3 유래(타임라인) 또는 비유(피자)
    if "history" in d:
        h = d["history"]
        items = "".join(f'<div><small>{e(x["date"])}</small><strong>{e(x["t"])}</strong><span>{e(x["s"])}</span></div>' for x in h["items"])
        P.append(f"""{head(d)}<div class="lbl">{e(h.get('label', '어디서 왔을까?'))}</div>
      <h2>{e(h['title'])}</h2><div class="tl">{items}</div>
      <div class="box">{h['point_html']}</div>{foot(3, T)}""")
    else:
      a, b = d["analogy"]["before"], d["analogy"]["after"]
      P.append(f"""{head(d)}<div class="lbl">피자로 이해하기 🍕</div>
      <h2>{e(d['analogy']['title'])}</h2>
      <div class="pz"><figure>{pizza(a['slices'], a['mine'])}<figcaption>{e(a['label'])}<span>{e(a['note'])}</span></figcaption></figure>
        <div class="arrow">→</div>
        <figure>{pizza(b['slices'], b['mine'])}<figcaption>{e(b['label'])}<span>{e(b['note'])}</span></figcaption></figure></div>
      <div class="box">{d['analogy']['point_html']}</div>{foot(3, T)}""")
    # 4 언제 생기나
    rows = "".join(f'<div class="row"><b>{i+1}</b><div>{e(x["t"])}<small>{e(x["s"])}</small></div></div>' for i, x in enumerate(d["when"]))
    P.append(f"""{head(d)}<div class="lbl">{e(d.get('when_label', '이럴 때 생겨요'))}</div><h2>{e(d['when_title'])}</h2>
      <div style="margin-top:30px">{rows}</div>{foot(4, T)}""")
    # 5 실제 사례
    c = d["case"]
    stats = "".join(f'<div><strong style="color:{s.get("color", INK)}">{e(s["v"])}</strong><span>{e(s["k"])}</span></div>' for s in c["stats"])
    P.append(f"""{head(d)}<div class="lbl">실제 사례 · {e(c['when'])}</div><h2>{e(c['title'])}</h2>
      <p style="margin-top:28px">{e(c['body'])}</p><div class="stat">{stats}</div>
      <div class="box">{c['point_html']}</div>{foot(5, T)}""")
    # 6 무조건 나쁜가?
    P.append(f"""{head(d)}<div class="lbl">{e(d.get('nuance_label', '그럼 무조건 나쁜 걸까?'))}</div><h2>{e(d['nuance']['title'])}</h2>
      <p>{e(d['nuance']['body'])}</p><div class="box">💡 <em>체크 질문</em><br>{e(d['nuance']['question'])}</div>{foot(6, T)}""")
    # 7 요약
    rows = "".join(f'<div class="row"><b>{i+1}</b><div>{e(x)}</div></div>' for i, x in enumerate(d["summary"]))
    P.append(f"""{head(d)}<h2 style="margin-top:40px">오늘의 용어 <span class="hl">{e(d['term'])}</span></h2>
      <div style="margin-top:20px">{rows}</div>
      <div class="box" style="margin-top:40px">📌 {e(d['tip'])}</div>
      <div class="foot"><span>정보 제공 목적이며 투자 권유가 아닙니다</span><span>{T}/{T}</span></div>""")
    return P

def caption(d):
    s = "\n".join(f"{i+1}. {x}" for i, x in enumerate(d["summary"]))
    return (f"{d['cover']['title'].replace(chr(10), ' ')} 🤔\n\n"
            f"오늘의 경제용어: {d['term']}\n{d['define_plain']}\n\n{s}\n\n"
            f"📌 {d['tip']}\n\n"
            f"매일 밤 9시, 오늘 시장에 나온 경제용어 하나씩 쉽게 풀어드려요.\n"
            f"저장해두고 팔로우하세요 👉 {HANDLE}\n\n"
            f"※ 정보 제공 목적이며 투자 권유가 아닙니다.\n\n"
            f"#경제용어 #경제공부 #주식공부 #주린이 #재테크 #{d['term'].replace(' ', '')} {d.get('tags', '')} #스톡와이")

def threads_text(d):
    s = "\n".join(f"{i+1}. {x}" for i, x in enumerate(d["summary"]))
    return (f"{d['cover']['title'].replace(chr(10), ' ')}\n\n오늘의 경제용어: {d['term']}\n"
            f"{d['define_plain']}\n\n{s}\n\n※ 정보 제공 목적, 투자 권유 아님")[:500]

def main(path):
    d = json.loads(pathlib.Path(path).read_text())
    pid = pathlib.Path(path).stem
    out, work = ROOT / "posts" / pid, ROOT / "build" / pid
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True); work.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1350})
        for i, h in enumerate(pages(d), 1):
            pg.set_content(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{h}</body></html>")
            pg.screenshot(path=str(work / f"card_{i:02d}.png"))
        br.close()
    make_reel(work)
    cards = []
    for pth in sorted(work.glob("card_*.png")):
        jp = out / (pth.stem + ".jpg"); Image.open(pth).convert("RGB").save(jp, "JPEG", quality=92, optimize=True); cards.append(jp.name)
    shutil.copy(work / "reel.mp4", out / "reel.mp4")
    (out / "caption.txt").write_text(caption(d))
    (out / "threads.txt").write_text(threads_text(d))
    (out / "post.json").write_text(json.dumps({"id": pid, "cards": cards, "reel": "reel.mp4",
                                               "reel_share_to_feed": False, "publish": True}, ensure_ascii=False, indent=2))
    print("term post ready:", out)

if __name__ == "__main__":
    main(sys.argv[1])
