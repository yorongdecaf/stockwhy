"""Stock, Why? 카드 시스템 v2 — 브랜드 키트 + 템플릿 5종 (1080×1350, 인스타 4:5)

design-and-templates 원칙: 브랜드 키트를 먼저 고정 → 실제로 올리는 형식만 템플릿화 →
템플릿마다 초점 하나·정해진 글자 크기 단계·높은 대비·안전 여백 → 글자만 바꿔 끼우면 끝.

사용:  python generator/cards_v2.py <spec.json> <out.jpg>
spec 예시는 data/card_samples/*.json  (template: number | quote | ranking | calendar | flash)
⚠️ 이 스크립트는 posts/ 나 post.json 을 만들지 않는다 (자동 게시 방지).
"""
import json, sys, html as _h, pathlib

# ── 브랜드 키트 (토큰) ─────────────────────────────────────────
KIT = {
    "bg": "#151515", "surface": "#232323", "line": "#333333",
    "text": "#FFFFFF", "sub": "#B4B4B4", "mute": "#7A7A7A",
    "accent": "#FFE14D",            # 노랑: 핵심 단어·결론
    "up": "#FF4D5E", "down": "#4D8BFF",   # 어두운 배경에서 대비를 위해 브랜드 빨강·파랑을 한 단계 밝게
    "font": "'Noto Sans CJK KR',sans-serif",   # 폰트 1종, 굵기만 900/700/400
    "margin": 72,
    # 글자 크기 단계 (px @1080 폭): 초점 / 제목 / 소제목 / 본문 / 메타
    "focal": 200, "h1": 96, "h2": 44, "body": 32, "meta": 24,
}
TAGS = {  # 템플릿별 꼬리표 (색으로 종류 구분)
    "number": ("오늘의 종목", "accent"), "quote": ("뉴스 해설", "accent"),
    "ranking": ("순위판", "accent"), "calendar": ("앞으로 볼 일정", "accent"),
    "flash": ("방금 나온 뉴스", "up"),
}
K = KIT
e = lambda s: _h.escape(str(s)).replace("\n", "<br>")


def mark(t):
    """*강조* → 노랑, [+숫자] / [-숫자] → 상승·하락 색"""
    import re
    t = e(t)
    t = re.sub(r"\*(.+?)\*", lambda m: f'<span style="color:{K["accent"]}">{m.group(1)}</span>', t)
    t = re.sub(r"\[([+-][^\]]+)\]", lambda m: f'<span style="color:{K["up"] if m.group(1)[0]=="+" else K["down"]}">{m.group(1)}</span>', t)
    return t


def frame(tpl, spec, body):
    tag, tc = TAGS[tpl]
    tag = spec.get("tag", tag)
    date = spec.get("date", "")
    concl = spec.get("conclusion", "")
    src = spec.get("source", "")
    return f"""<html><head><meta charset='utf-8'><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;background:{K['bg']};color:{K['text']};font-family:{K['font']};
 padding:{K['margin']-8}px {K['margin']}px 52px;display:flex;flex-direction:column;overflow:hidden}}
.row{{display:flex;gap:22px;align-items:flex-start;padding:24px 0;border-top:2px solid {K['line']}}}
.n{{flex:none;width:44px;font-size:34px;font-weight:900;color:{K['accent']}}}
.rt{{font-size:{K['body']+4}px;font-weight:900;line-height:1.3}}
.rs{{margin-top:6px;font-size:{K['meta']+3}px;color:{K['sub']};line-height:1.4}}
</style></head><body>
<div style="display:flex;justify-content:space-between;align-items:center">
 <span style="display:flex;align-items:center;gap:14px">
  <span style="background:{K[tc]};color:{K['bg']};font-weight:900;font-size:{K['meta']+4}px;padding:7px 16px;border-radius:6px">{e(tag)}</span>
  <span style="font-size:{K['meta']+2}px;font-weight:700;color:{K['sub']}">{e(date)}</span></span>
 <span style="font-weight:900;font-size:30px">Stock, Why<span style="display:inline-flex;width:40px;height:40px;margin-left:8px;border-radius:50%;
  background:{K['accent']};color:{K['bg']};align-items:center;justify-content:center;font-size:28px">?</span></span></div>
{body}
{f'''<div style="margin-top:auto;background:{K['accent']};color:{K['bg']};border-radius:20px;padding:26px 32px">
 <div style="font-size:{K['meta']}px;font-weight:900">결론</div>
 <div style="margin-top:4px;font-size:{K['h2']-4}px;font-weight:900;line-height:1.3">{mark(concl)}</div></div>''' if concl else '<div style="margin-top:auto"></div>'}
<div style="margin-top:18px;display:flex;justify-content:space-between;gap:20px;font-size:{K['meta']-2}px;color:{K['mute']}">
 <span>{e(src)}{' · ' if src else ''}정보 제공 목적 · 투자 권유 아님</span><span style="flex:none">@stock.why.daily</span></div>
</body></html>"""


def rows(items):
    return "".join(f'<div class="row"><span class="n">{i}</span><div><div class="rt">{mark(r[0])}</div>'
                   + (f'<div class="rs">{mark(r[1])}</div>' if len(r) > 1 and r[1] else "") + "</div></div>"
                   for i, r in enumerate(items, 1))


# ── 템플릿 5종 ─────────────────────────────────────────────
def t_number(s):
    col = K["up"] if s["number"].startswith("+") else K["down"] if s["number"].startswith("-") else K["accent"]
    fs = K["focal"] if len(s["number"]) <= 6 else int(K["focal"] * 0.78)
    return f"""
<div style="margin-top:40px;font-size:{K['h2']-12}px;font-weight:700;color:{K['sub']}">{mark(s.get('kicker',''))}</div>
<div style="margin-top:2px;font-size:{fs}px;font-weight:900;letter-spacing:-8px;line-height:1;color:{col}">{e(s['number'])}</div>
<div style="margin-top:6px;font-size:{K['meta']+2}px;color:{K['sub']}">{mark(s.get('number_sub',''))}</div>
<div style="margin-top:30px;font-size:{K['h1']-30}px;font-weight:900;line-height:1.15;letter-spacing:-1.5px">{mark(s['headline'])}</div>
<div style="margin-top:22px">{rows(s.get('rows', []))}</div>"""


def t_quote(s):
    bar = ""
    if s.get("bar"):
        b = s["bar"]
        bar = f"""<div style="margin-top:16px;display:flex;height:28px;border-radius:14px;overflow:hidden;background:{K['surface']}">
 <div style="flex:{100-b['pct']};background:#555"></div><div style="flex:{b['pct']};background:{K['up']}"></div></div>
<div style="margin-top:10px;display:flex;justify-content:space-between;font-size:{K['meta']}px;color:{K['sub']}"><span>{e(b['left'])}</span><span>{e(b['right'])}</span></div>"""
    return f"""
<div style="margin-top:54px;font-size:200px;font-weight:900;line-height:.55;color:{K['accent']}">“</div>
<div style="margin-top:4px;font-size:{K['h1']+16}px;font-weight:900;line-height:1.12;letter-spacing:-3px">{mark(s['quote'])}<span style="color:{K['accent']}">”</span></div>
<div style="margin-top:28px;font-size:{K['body']-2}px;font-weight:700;color:#D6D6D6">— {e(s['who'])}</div>
<div style="margin-top:4px;font-size:{K['meta']+1}px;color:{K['sub']}">{e(s.get('context',''))}</div>
<div style="margin-top:36px;border-top:2px solid {K['line']};padding-top:28px;font-size:{K['h2']-4}px;font-weight:900">{mark(s.get('twist',''))}</div>
{bar}"""


def t_ranking(s):
    allv = [abs(float(x[1].replace('%', ''))) for x in s["up"] + s["down"]] or [1]
    mx = max(allv)

    def bars(items, col):
        out = ""
        for i, (name, v) in enumerate(items, 1):
            w = max(5, abs(float(v.replace('%', ''))) / mx * 100)
            out += f"""<div style="display:flex;align-items:center;height:54px;gap:16px">
 <span style="width:26px;font-size:26px;font-weight:900;color:{col}">{i}</span>
 <span style="width:250px;font-size:30px;font-weight:700;white-space:nowrap">{e(name)}</span>
 <span style="flex:1;height:26px;position:relative"><span style="position:absolute;left:0;top:0;bottom:0;width:{w:.0f}%;background:{col};border-radius:5px;opacity:{1 if i==1 else .5}"></span></span>
 <span style="width:136px;text-align:right;font-size:32px;font-weight:900;color:{col}">{e(v)}</span></div>"""
        return out
    return f"""
<div style="margin-top:36px;font-size:{K['h1']-16}px;font-weight:900;line-height:1.15;letter-spacing:-2px">{mark(s['headline'])}</div>
<div style="margin-top:12px;font-size:{K['meta']+2}px;color:{K['sub']}">{mark(s.get('sub',''))}</div>
<div style="margin-top:24px;font-size:28px;font-weight:900;color:{K['up']}">▲ {e(s.get('up_label','많이 오른 TOP5'))}</div>{bars(s['up'], K['up'])}
<div style="margin-top:14px;font-size:28px;font-weight:900;color:{K['down']}">▼ {e(s.get('down_label','많이 내린 TOP5'))}</div>{bars(s['down'], K['down'])}"""


def t_calendar(s):
    ev = "".join(f"""<div style="display:flex;gap:26px;align-items:stretch;margin-top:44px">
 <div style="flex:none;width:220px;background:{K["surface"]};border-radius:18px;padding:26px 0;text-align:center;border:3px solid {K['accent'] if i==0 else K['line']}">
  <div style="font-size:{K['meta']}px;color:{K['sub']};font-weight:700">{e(x['dow'])}</div>
  <div style="font-size:64px;font-weight:900;line-height:1.1">{e(x['day'])}</div>
  <div style="font-size:{K['meta']}px;color:{K['accent']};font-weight:900">{e(x.get('dday',''))}</div></div>
 <div style="padding-top:8px"><div style="font-size:{K['body']+6}px;font-weight:900;line-height:1.3">{mark(x['title'])}</div>
  <div style="margin-top:8px;font-size:{K['meta']+3}px;color:{K['sub']};line-height:1.45">{mark(x.get('why',''))}</div></div></div>"""
                 for i, x in enumerate(s["events"]))
    return f"""
<div style="margin-top:40px;font-size:{K['h1']-10}px;font-weight:900;line-height:1.15;letter-spacing:-2px">{mark(s['headline'])}</div>
<div style="margin-top:12px;font-size:{K['meta']+2}px;color:{K['sub']}">{mark(s.get('sub',''))}</div>
<div style="margin-top:16px">{ev}</div>"""


def t_flash(s):
    chips = "".join(f'<span style="display:inline-block;margin:0 12px 12px 0;padding:10px 18px;border-radius:12px;background:{K["surface"]};'
                    f'font-size:{K["body"]-2}px;font-weight:800"><span style="color:{K["sub"]};font-size:{K["meta"]}px">{e(a)}</span> {mark(b)}</span>'
                    for a, b in s.get("chips", []))
    return f"""
<div style="margin-top:44px;font-size:{K['h2']-12}px;font-weight:700;color:{K['sub']}">{mark(s.get('kicker',''))}</div>
<div style="margin-top:8px;font-size:{K['h1']}px;font-weight:900;line-height:1.12;letter-spacing:-2.5px">{mark(s['headline'])}</div>
<div style="margin-top:28px">{chips}</div>
<div style="margin-top:12px">{rows(s.get('rows', []))}</div>"""


TEMPLATES = {"number": t_number, "quote": t_quote, "ranking": t_ranking, "calendar": t_calendar, "flash": t_flash}


def build_html(spec):
    return frame(spec["template"], spec, TEMPLATES[spec["template"]](spec))


def render(spec, out):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    out = pathlib.Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    assert "posts" not in out.parts, "posts/ 에는 저장하지 않는다 (자동 게시 방지)"
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1350})
        pg.set_content(build_html(spec)); pg.wait_for_timeout(300)
        png = out.with_suffix(".png"); pg.screenshot(path=str(png)); br.close()
    Image.open(png).convert("RGB").save(out, quality=93); png.unlink()
    return out


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    print(render(spec, sys.argv[2]))
