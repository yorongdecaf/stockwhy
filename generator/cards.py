"""Stock, Why? 카드뉴스 (1080x1350, 8장) + 프로필 이미지
사용법: python3 cards.py data/kr_2026-10-29.json out/kr_2026-10-29
"""
import json, sys, html, pathlib
from playwright.sync_api import sync_playwright
from brand import *

def e(s): return html.escape(s).replace("\n", "<br>")

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1350px;overflow:hidden;word-break:keep-all}}
body{{font-family:{FONT};background:{PAPER};color:{INK};padding:84px 92px 0;display:flex;flex-direction:column;position:relative}}
.hl{{background:linear-gradient(transparent 60%,{YELLOW} 60%)}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.chip{{font-size:30px;font-weight:900;color:#fff;padding:12px 26px;border-radius:999px}}
.date{{font-size:28px;font-weight:700;color:{GRAY}}}
.foot{{position:absolute;left:92px;right:92px;bottom:60px;display:flex;justify-content:space-between;align-items:center;
  font-size:24px;color:#A0A0A0;font-weight:700}}
.ctitle{{font-size:100px;font-weight:900;line-height:1.2;letter-spacing:-3px;margin-top:auto}}
.csub{{font-size:40px;font-weight:700;color:#444;margin:44px 0 170px}}
.cbox{{display:flex;gap:16px;margin-top:40px}}
.cbox span{{font-size:30px;font-weight:900;padding:12px 24px;border:3px solid;border-radius:14px}}
.name{{font-size:96px;font-weight:900;letter-spacing:-3px;line-height:1.1;margin-top:64px}}
.code{{font-size:32px;color:#9A9A9A;font-weight:700;margin-top:14px}}
.pct{{font-size:150px;font-weight:900;letter-spacing:-5px;line-height:1;margin:34px 0 54px}}
.lbl{{font-size:30px;font-weight:900;color:{GRAY};margin-bottom:14px}}
.what{{font-size:40px;font-weight:700;line-height:1.45;padding-bottom:40px;border-bottom:3px solid {INK};margin-bottom:40px}}
.why{{display:flex;gap:22px;font-size:42px;line-height:1.45;margin:18px 0;color:#2A2A2A}}
.why b{{flex:none;width:46px;height:46px;border-radius:50%;background:{YELLOW};color:{INK};
  font-size:28px;display:flex;align-items:center;justify-content:center;margin-top:5px}}
.stitle{{font-size:72px;font-weight:900;letter-spacing:-2px;line-height:1.25;margin:36px 0 16px}}
.grp{{font-size:30px;font-weight:900;margin:22px 0 4px}}
.r{{display:flex;justify-content:space-between;font-size:40px;font-weight:700;padding:15px 0;border-bottom:2px solid #DDD8CC}}
.r span:last-child{{font-weight:900}}
.take{{margin-top:34px;background:{INK};color:#fff;border-radius:22px;padding:28px 36px;font-size:34px;font-weight:700;line-height:1.5}}
.take em{{font-style:normal;color:{YELLOW}}}
"""

def up_label(d): return d.get("up_label", "상승")   # 폭락장 등에서는 "선방"
def up_mark(d): return "▲" if up_label(d) == "상승" else "●"
def sign_color(chg): return DOWN if chg.strip().startswith("-") else UP

def foot(left, right):
    return f'<div class="foot"><span>{left}</span><span>{right}</span></div>'

def cover(d):
    return f"""<div class="top">{logo(40)}<span class="date">{e(d['date'])}</span></div>
    <div class="ctitle">{e(d['cover']['title'])}</div>
    <div class="cbox"><span style="color:{UP}">{up_mark(d)} {up_label(d)} TOP3</span><span style="color:{DOWN}">▼ 하락 TOP3</span></div>
    <div class="csub">{e(d['cover']['sub'])}</div>
    {foot(HANDLE, '넘겨보기 →')}"""

def stock(d, s, rank, up, page):
    c = UP if up else DOWN
    neg = s["chg"].strip().startswith("-")
    pc = DOWN if neg else UP                      # 등락률 색·화살표는 실제 부호대로
    verb = ("올랐을까?" if up_label(d) == "상승" else "선방했을까?") if up else "떨어졌을까?"
    whys = "".join(f'<div class="why"><b>{i+1}</b><span>{e(w)}</span></div>' for i, w in enumerate(s["why"]))
    return f"""<div class="top"><span class="chip" style="background:{c}">{d['label']} {up_label(d) if up else '하락'} {rank}위</span>
      <span class="date">{e(d['date'])}</span></div>
    <div class="name">{e(s['name'])}</div><div class="code">{e(s['code'])}</div>
    <div class="pct" style="color:{pc}"><span style="font-size:.55em;vertical-align:.32em;margin-right:14px">{'▼' if neg else '▲'}</span>{e(s['chg'].lstrip('+-'))}</div>
    <div class="lbl">어떤 회사?</div><div class="what">{e(s['what'])}</div>
    <div class="lbl">왜 <span class="hl" style="color:{INK}">{verb}</span></div>{whys}
    {foot(logo(24) + f'&nbsp;&nbsp;<span style="font-size:22px">{HANDLE}</span>', f'{page}/8')}"""

def summary(d):
    rows = lambda arr, c: "".join(f'<div class="r"><span>{e(s["name"])}</span><span style="color:{sign_color(s["chg"])}">{e(s["chg"])}</span></div>' for s in arr)
    return f"""<div class="top"><span class="chip" style="background:{INK}">한눈에 정리</span><span class="date">{e(d['date'])}</span></div>
    <div class="stitle">오늘의 {d['label']} <span class="hl">TOP 3</span></div>
    <div class="grp" style="color:{UP}">{up_mark(d)} {up_label(d)}</div>{rows(d['up'], UP)}
    <div class="grp" style="color:{DOWN}">▼ 하락</div>{rows(d['down'], DOWN)}
    <div class="take">💡 <em>한 줄 정리</em><br>{e(d['takeaway'])}</div>
    {foot('정보 제공 목적이며 투자 권유가 아닙니다 · ' + e(d['universe']), '8/8')}"""

def pages(d):
    out = [cover(d)]
    out += [stock(d, s, i + 1, True, i + 2) for i, s in enumerate(d["up"])]
    out += [stock(d, s, i + 1, False, i + 5) for i, s in enumerate(d["down"])]
    out.append(summary(d))
    return out

def render_cards(d, out):
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1350})
        for i, h in enumerate(pages(d), 1):
            pg.set_content(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{h}</body></html>")
            pg.screenshot(path=str(out / f"card_{i:02d}.png"))
        br.close()

def render_profile(path):
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 600, "height": 600})
        pg.set_content(f"<html><body style='margin:0'>{mascot_svg(600)}</body></html>")
        pg.screenshot(path=str(path)); br.close()

if __name__ == "__main__":
    d = json.loads(pathlib.Path(sys.argv[1]).read_text())
    out = pathlib.Path(sys.argv[2])
    render_cards(d, out)
    render_profile(out / "profile.png")
    print("cards ok", out)
