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
# ── 테마: 같은 템플릿에 다른 브랜드 키트를 입힌다 (spec의 "theme" 또는 기본 dark) ──
_GRAIN = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>"
          "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3'/>"
          "<feColorMatrix values='0 0 0 0 .23  0 0 0 0 .14  0 0 0 0 .09  0 0 0 .22 0'/></filter>"
          "<rect width='300' height='300' filter='url(%23n)'/></svg>\")")
THEMES = {
    "dark": dict(bg="#151515", surface="#232323", line="#333333", text="#FFFFFF", sub="#B4B4B4", mute="#7A7A7A",
                 accent="#FFE14D", tag_fg="#151515", num="#FFE14D", up="#FF4D5E", down="#4D8BFF",
                 concl_bg="#FFE14D", concl_fg="#151515", concl_label="#151515", bar_rest="#555555",
                 shadow="none", radius=20, deco="", strip=""),
    "retro": dict(bg="#F3E4C4", surface="#FBF1DC", line="#3A2418", text="#3A2418", sub="#6B5444", mute="#8A7462",
                  accent="#E8702A", tag_fg="#F3E4C4", num="#C8372D", up="#C8372D", down="#2B5FA8",
                  concl_bg="#3A2418", concl_fg="#F3E4C4", concl_label="#F2B33D", bar_rest="#D9C7A3",
                  shadow="8px 8px 0 #3A2418", radius=18,
                  deco=("<div style=\"position:absolute;left:50%;top:560px;width:2600px;height:2600px;transform:translate(-50%,-50%);"
                        "background:repeating-conic-gradient(from 0deg,#F2B33D 0deg 7deg,transparent 7deg 15deg);opacity:.32;"
                        "-webkit-mask:radial-gradient(circle,#000 10%,transparent 42%);z-index:0\"></div>"
                        "<style>.grain{position:absolute;inset:0;background-image:" + _GRAIN + ";mix-blend-mode:multiply;z-index:9;pointer-events:none}</style><div class=\"grain\"></div>"
                        "<div style=\"position:absolute;inset:20px;border:5px solid #3A2418;border-radius:26px;z-index:8;pointer-events:none\"></div>"),
                  strip="".join(f'<div style="height:12px;background:{c}"></div>' for c in ("#C8372D", "#E8702A", "#F2B33D", "#2B7A78"))),
    # 스위스 모던: 흰 종이 + 검정 + 빨강, 직각, 굵은 막대
    "swiss": dict(bg="#F4F3EF", surface="#FFFFFF", line="#111111", text="#111111", sub="#555555", mute="#888888",
                  accent="#E30613", tag_fg="#FFFFFF", num="#E30613", up="#E30613", down="#1F4FD8",
                  concl_bg="#111111", concl_fg="#FFFFFF", concl_label="#E30613", bar_rest="#D6D4CE",
                  shadow="none", radius=0,
                  deco=('<div style="position:absolute;right:-180px;top:330px;width:560px;height:560px;border-radius:50%;background:#E30613;opacity:.10;z-index:0"></div>'
                        '<div style="position:absolute;left:0;top:0;bottom:0;width:18px;background:#111;z-index:3"></div>'),
                  strip='<div style="height:10px;background:#111"></div>'),
    # 오답노트: 줄 노트 + 빨간 펜 + 형광펜 결론
    "notebook": dict(bg="#FDFBF3", surface="#FFFFFF", line="#9BB7D9", text="#22262E", sub="#5A6170", mute="#8A90A0",
                  accent="#E23B3B", tag_fg="#FFFFFF", num="#E23B3B", up="#E23B3B", down="#2F5FD0",
                  concl_bg="#FFF06A", concl_fg="#22262E", concl_label="#E23B3B", bar_rest="#E3E7EE",
                  shadow="none", radius=4,
                  deco=('<div style="position:absolute;inset:0;background:repeating-linear-gradient(180deg,transparent 0 51px,#CFDDEF 51px 53px);z-index:0"></div>'
                        '<div style="position:absolute;left:52px;top:0;bottom:0;width:3px;background:#F2A0A0;z-index:0"></div>'
                        '<div style="position:absolute;left:40px;top:222px;width:800px;height:230px;border:6px solid #E23B3B;border-radius:50%;transform:rotate(-3deg);opacity:.5;z-index:1"></div>'),
                  strip=""),
    # 네온: 남색 밤 + 형광 핑크·시안 발광
    "neon": dict(bg="#0B0A1F", surface="#16143A", line="#2E2A66", text="#EFEAFF", sub="#A9A3D6", mute="#6F69A3",
                  accent="#FF3FD8", tag_fg="#0B0A1F", num="#29E3FF", up="#FF4F7B", down="#29E3FF",
                  concl_bg="#0B0A1F", concl_fg="#EFEAFF", concl_label="#29E3FF", bar_rest="#2E2A66",
                  shadow="0 0 28px rgba(41,227,255,.55)", radius=22, concl_border="3px solid #29E3FF",
                  deco=('<style>span{text-shadow:0 0 1px currentColor}</style>'
                        '<div style="position:absolute;left:-200px;top:200px;width:700px;height:700px;border-radius:50%;background:radial-gradient(circle,rgba(255,63,216,.28),transparent 65%);z-index:0"></div>'
                        '<div style="position:absolute;right:-240px;bottom:120px;width:760px;height:760px;border-radius:50%;background:radial-gradient(circle,rgba(41,227,255,.22),transparent 65%);z-index:0"></div>'
                        '<div style="position:absolute;left:0;right:0;bottom:0;height:420px;background:repeating-linear-gradient(90deg,rgba(255,63,216,.18) 0 2px,transparent 2px 90px),repeating-linear-gradient(0deg,rgba(255,63,216,.18) 0 2px,transparent 2px 60px);'
                        '-webkit-mask:linear-gradient(transparent,#000);z-index:0"></div>'),
                  strip='<div style="height:4px;background:linear-gradient(90deg,#FF3FD8,#29E3FF);box-shadow:0 0 18px #FF3FD8"></div>'),
    # 증권사 시세 전광판: 검정 LED 판 + 주황 도트 글씨
    "ledboard": dict(bg="#070707", surface="#141414", line="#2A2A2A", text="#FFB43B", sub="#C98A2E", mute="#7A5A2A",
                  accent="#FFE14D", tag_fg="#070707", num="#FFE14D", up="#FF3B3B", down="#33A8FF",
                  concl_bg="#141414", concl_fg="#FFB43B", concl_label="#FFE14D", bar_rest="#2A2A2A",
                  shadow="none", radius=6, concl_border="3px solid #FFB43B",
                  font="'DejaVu Sans Mono','Noto Sans CJK KR',monospace",
                  deco=('<div style="position:absolute;inset:0;background:radial-gradient(circle,rgba(0,0,0,.55) 1.3px,transparent 1.6px) 0 0/6px 6px;z-index:6;pointer-events:none"></div>'
                        '<div style="position:absolute;inset:14px;border:10px solid #222;border-radius:14px;box-shadow:inset 0 0 0 3px #333;z-index:7;pointer-events:none"></div>'
                        '<style>body>div:last-child span{font-size:17px;letter-spacing:-1px}</style>'),
                  strip='<div style="height:6px;background:repeating-linear-gradient(90deg,#FFB43B 0 14px,transparent 14px 22px)"></div>'),
    # 모바일 앱 카드: 밝은 회색 + 둥근 흰 카드 + 보라 포인트
    "app": dict(bg="#ECEFF5", surface="#FFFFFF", line="#DCE1EA", text="#1B1D21", sub="#626B7A", mute="#98A0AE",
                  accent="#6A4CFF", tag_fg="#FFFFFF", num="#6A4CFF", up="#F0384F", down="#2C7BE5",
                  concl_bg="#F1EDFF", concl_fg="#1B1D21", concl_label="#6A4CFF", bar_rest="#DCE1EA",
                  shadow="none", radius=28,
                  deco=('<div style="position:absolute;left:40px;right:40px;top:142px;bottom:96px;background:#FFFFFF;border-radius:44px;'
                        'box-shadow:0 18px 48px rgba(27,29,33,.08);z-index:0"></div>'),
                  strip=""),
}


TAGS = {  # 템플릿별 꼬리표 (색으로 종류 구분)
    "number": ("오늘의 종목", "accent"), "quote": ("뉴스 해설", "accent"),
    "ranking": ("순위판", "accent"), "calendar": ("앞으로 볼 일정", "accent"),
    "flash": ("방금 나온 뉴스", "up"),
}
K = dict(KIT)


def use_theme(name):
    K.update(KIT); K.update(THEMES.get(name or "dark", THEMES["dark"]))


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
body{{position:relative;width:1080px;height:1350px;background:{K['bg']};color:{K['text']};font-family:{K['font']};
 padding:{K['margin']-8}px {K['margin']}px 52px;display:flex;flex-direction:column;overflow:hidden}}
.row{{display:flex;gap:22px;align-items:flex-start;padding:24px 0;border-top:2px solid {K['line']}}}
.n{{flex:none;width:44px;font-size:34px;font-weight:900;color:{K['num']}}}
body>*{{position:relative;z-index:2}}
.rt{{font-size:{K['body']+4}px;font-weight:900;line-height:1.3}}
.rs{{margin-top:6px;font-size:{K['meta']+3}px;color:{K['sub']};line-height:1.4}}
</style></head><body>{K['deco']}
<div style="display:flex;justify-content:space-between;align-items:center">
 <span style="display:flex;align-items:center;gap:14px">
  <span style="background:{K[tc]};color:{K['tag_fg']};font-weight:900;font-size:{K['meta']+4}px;padding:7px 16px;border-radius:6px">{e(tag)}</span>
  <span style="font-size:{K['meta']+2}px;font-weight:700;color:{K['sub']}">{e(date)}</span></span>
 <span style="font-weight:900;font-size:30px">Stock, Why<span style="display:inline-flex;width:40px;height:40px;margin-left:8px;border-radius:50%;
  background:{K['accent']};color:{K['tag_fg']};align-items:center;justify-content:center;font-size:28px">?</span></span></div>
{f'<div style="margin:22px -{K["margin"]}px 0">{K["strip"]}</div>' if K['strip'] else ''}
{body}
{f'''<div style="margin-top:auto;background:{K['concl_bg']};color:{K['concl_fg']};border-radius:{K['radius']}px;padding:26px 32px;box-shadow:{K['shadow']};border:{K.get('concl_border','none')}">
 <div style="font-size:{K['meta']}px;font-weight:900;color:{K['concl_label']}">결론</div>
 <div style="margin-top:4px;font-size:{K['h2']-4}px;font-weight:900;line-height:1.3">{e(concl).replace("*","")}</div></div>''' if concl else '<div style="margin-top:auto"></div>'}
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
 <div style="flex:{100-b['pct']};background:{K['bar_rest']}"></div><div style="flex:{b['pct']};background:{K['up']}"></div></div>
<div style="margin-top:10px;display:flex;justify-content:space-between;font-size:{K['meta']}px;color:{K['sub']}"><span>{e(b['left'])}</span><span>{e(b['right'])}</span></div>"""
    return f"""
<div style="margin-top:54px;font-size:200px;font-weight:900;line-height:.55;color:{K['accent']}">“</div>
<div style="margin-top:4px;font-size:{K['h1']+16}px;font-weight:900;line-height:1.12;letter-spacing:-3px">{mark(s['quote'])}<span style="color:{K['accent']}">”</span></div>
<div style="margin-top:28px;font-size:{K['body']-2}px;font-weight:700;color:{K['text']}">— {e(s['who'])}</div>
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
 <div style="flex:none;width:220px;background:{K["surface"]};border-radius:18px;padding:26px 0;text-align:center;border:3px solid {K['accent'] if i==0 else K['line']};box-shadow:{K['shadow'] if i==0 else 'none'}">
  <div style="font-size:{K['meta']}px;color:{K['sub']};font-weight:700">{e(x['dow'])}</div>
  <div style="font-size:64px;font-weight:900;line-height:1.1">{e(x['day'])}</div>
  <div style="font-size:{K['meta']}px;color:{K['num']};font-weight:900">{e(x.get('dday',''))}</div></div>
 <div style="padding-top:8px"><div style="font-size:{K['body']+6}px;font-weight:900;line-height:1.3">{mark(x['title'])}</div>
  <div style="margin-top:8px;font-size:{K['meta']+3}px;color:{K['sub']};line-height:1.45">{mark(x.get('why',''))}</div></div></div>"""
                 for i, x in enumerate(s["events"]))
    return f"""
<div style="margin-top:40px;font-size:{K['h1']-10}px;font-weight:900;line-height:1.15;letter-spacing:-2px">{mark(s['headline'])}</div>
<div style="margin-top:12px;font-size:{K['meta']+2}px;color:{K['sub']}">{mark(s.get('sub',''))}</div>
<div style="margin-top:16px">{ev}</div>"""


def t_flash(s):
    chips = "".join(f'<span style="display:inline-block;margin:0 12px 12px 0;padding:10px 18px;border-radius:12px;background:{K["surface"]};'
                    f'font-size:{K["body"]-2}px;font-weight:800;border:2px solid {K["line"]}"><span style="color:{K["sub"]};font-size:{K["meta"]}px">{e(a)}</span> {mark(b)}</span>'
                    for a, b in s.get("chips", []))
    return f"""
<div style="margin-top:44px;font-size:{K['h2']-12}px;font-weight:700;color:{K['sub']}">{mark(s.get('kicker',''))}</div>
<div style="margin-top:8px;font-size:{K['h1']}px;font-weight:900;line-height:1.12;letter-spacing:-2.5px">{mark(s['headline'])}</div>
<div style="margin-top:28px">{chips}</div>
<div style="margin-top:12px">{rows(s.get('rows', []))}</div>"""


TEMPLATES = {"number": t_number, "quote": t_quote, "ranking": t_ranking, "calendar": t_calendar, "flash": t_flash}


def build_html(spec):
    use_theme(spec.get("theme"))
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
    if len(sys.argv) > 3:
        spec["theme"] = sys.argv[3]   # 예: python generator/cards_v2.py spec.json out.jpg retro
    print(render(spec, sys.argv[2]))
