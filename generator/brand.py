"""Stock, Why? 브랜드 공통 요소 (색, 로고, 핸들)"""

NAME = "Stock, Why?"
HANDLE = "@stock.why.daily"
SLOGAN = "주식아, 왜 올랐니? 왜 내렸니?"

INK = "#151515"        # 메인 검정
PAPER = "#FAF8F3"      # 아이보리 배경
YELLOW = "#FFE14D"     # 포인트(형광펜)
UP = "#E8344E"         # 상승 = 빨강 (한국식)
DOWN = "#2F6BFF"       # 하락 = 파랑
GRAY = "#8C8C8C"

FONT = "'Noto Sans CJK KR','Noto Sans KR',sans-serif"


def logo(size=34, dark=False):
    """가로형 워드마크: Stock, Why(?) — 물음표는 노란 원 배지"""
    ink = "#FFFFFF" if dark else INK
    b = int(size * 1.25)
    return (f'<span style="display:inline-flex;align-items:center;gap:{int(size*0.12)}px;'
            f'font-family:{FONT};font-weight:900;font-size:{size}px;letter-spacing:-0.5px;color:{ink};line-height:1">'
            f'Stock, Why'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;width:{b}px;height:{b}px;'
            f'border-radius:50%;background:{YELLOW};color:{INK};font-size:{int(size*0.95)}px;margin-left:{int(size*0.08)}px">?</span>'
            f'</span>')


def mascot_svg(px=600):
    """물음표 마스코트 '와이' — 노란 원에 큰 ?, 양옆 ▲▼"""
    return f"""<svg width="{px}" height="{px}" viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg">
  <rect width="600" height="600" fill="{PAPER}"/>
  <circle cx="300" cy="300" r="250" fill="{YELLOW}"/>
  <text x="300" y="398" text-anchor="middle" font-family="Noto Sans CJK KR" font-weight="900"
        font-size="330" fill="{INK}">?</text>
  <circle cx="262" cy="214" r="13" fill="{PAPER}"/><circle cx="326" cy="214" r="13" fill="{PAPER}"/>
  <polygon points="118,300 150,248 182,300" fill="{UP}"/>
  <polygon points="418,262 482,262 450,314" fill="{DOWN}"/>
</svg>"""
