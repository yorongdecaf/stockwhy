# Stock, Why? 📈📉

장 마감 후 오른 이유·내린 이유 TOP3 — 인스타그램 [@stock.why.daily](https://instagram.com/stock.why.daily)

## 구조
- `data/` 원고 (종목, 등락률, 원인)
- `generator/` 카드뉴스·릴스 생성 (`make_post.py data/xxx.json` → `posts/xxx/`)
- `posts/` 게시 준비 폴더 (카드 jpg 8장, reel.mp4, caption.txt, post.json)
- `publisher/` 인스타그램 공식 API 게시 스크립트
- `.github/workflows/publish.yml` posts/ 에 새 폴더가 올라오면 자동 게시
- `.github/workflows/token.yml` 매주 토큰 확인·연장

## 필요한 Secrets (Settings → Secrets and variables → Actions)
- `IG_ACCESS_TOKEN` 인스타그램 API 토큰
- `IG_USER_ID` 인스타그램 사용자 ID (숫자)
- `GH_PAT` (선택) 토큰 자동 교체용 GitHub 토큰

※ 정보 제공 목적이며 투자 권유가 아닙니다.
