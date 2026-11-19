# 매시간 뉴스 알림 작업 규칙 (Stock, Why?)

예약 작업 "Stock, Why? 매시간 뉴스 알림"이 매번 이 문서를 처음부터 읽고 그대로 따른다.
목적: 중요한 경제 뉴스가 나오면 **카드 1장 + 캡션**을 만들어 사용자에게 알린다. **게시는 사용자가 직접 한다.**

## 절대 규칙
- 인스타·스레드·어디에도 **업로드·게시하지 않는다.** `publish.yml` 실행 금지, `posts/` 폴더와 `post.json` 생성 금지.
- 브랜드 규칙은 `docs/brand-profile.md`를 따른다 (말투 '~다' 체, 금지어: 무조건·확실·100%·사세요·팔세요·목표가, 매수·매도 권유·주가 단정 예측 금지).
- 숫자·사실은 **공식 원문 또는 주요 언론 2곳 이상**에서 확인된 것만. 확인 못 하면 만들지 않는다.
- 인용은 실제 발언만, 발언자·날짜·매체 표기. 번역이면 "(번역)".
- 기사 본문을 그대로 옮기지 않는다. 짧게, 내 말로.
- 차단된 사이트를 curl·다른 경로로 우회하지 않는다.

## 1. 준비
1. 저장소 `yorongdecaf/stockwhy` (없으면 add_repo access=push, `git clone --depth 1 https://github.com/yorongdecaf/stockwhy /home/claude/stockwhy`), `git pull`.
2. `docs/brand-profile.md`, `data/alerts/state.json` 읽기.
3. 오늘(KST) `data/news/<YYYY-MM-DD>.json` 읽기. 파일이 없거나 `updated_at`이 90분보다 오래됐으면
   `gh api -X POST repos/yorongdecaf/stockwhy/actions/workflows/news.yml/dispatches -f ref=main` → 최대 5분 대기 → `git pull`.
   GitHub API는 REST(`gh api repos/...`)만 쓴다.

## 2. 새 기사 고르기
- 후보 = `state.json`의 `last_run_at` 이후 수집된 항목 중 `alerted_links`에 없는 것.
  (`published`가 비었거나 이상하면 링크 중복 여부만 본다)
- **알림 기준 (하나라도 해당하고, 사실 확인이 되는 것만):**
  1. 미국 연준·한국은행의 금리 결정, 성명, 회의록, 총재·이사의 금리·물가 발언
  2. 미국 CPI·고용, 한국 물가·성장률·수출 등 주요 지표 발표
  3. 코스피 시총 상위 30 종목의 실적·대형 계약·공시 (`data/prices/` 최신 kr 파일의 `all` 목록 기준), 미국 빅테크(엔비디아·애플·MS 등) 실적
  4. 시장 전체를 흔드는 사건: 지수 급변, 서킷브레이커, 환율 급변, 큰 정책 발표
- **제외:** 칼럼·사설·인사·행사, 이미 지난 알림과 같은 사건(후속 기사), 출처가 하나뿐이고 공식 원문도 아닌 것, 루머.
- 한 번 실행에 **최대 2건**. 같은 사건을 다룬 기사 여러 개는 1건으로 묶는다.

## 3. 사실 확인
- 고른 기사의 원문 링크를 WebFetch로 연다. 공식 원문(연준·한국은행·DART)이 있으면 그것까지 확인.
- 다른 주요 언론 1곳 이상에서 같은 숫자·내용을 WebSearch로 확인. 숫자가 서로 다르면 시점·기준을 밝히거나 범위로 쓴다.
- 확인이 안 되면 그 건은 건너뛴다 (state에 `skipped` 이유와 함께 기록).

## 4. 카드 만들기
- `generator/cards_v2.py`의 템플릿 중 하나를 고른다. 형식 예시는 `data/card_samples/*.json`.
  - `flash` 방금 나온 뉴스 (기본), `quote` 핵심이 발언일 때, `number` 핵심이 숫자 하나일 때, `calendar` 예정 일정, `ranking` 순위
- 카드 문구 규칙:
  - 제목(headline): 결론 대신 궁금증. 사실 자체가 센 것을 앞에. 한 줄 12자 안팎, 2~3줄, `\n` 줄바꿈. `*강조*`는 노랑, `[+3.2%]`/`[-1.5%]`는 상승·하락 색.
  - rows(정확히 3개 = 기·승·전): 제목 28자 안팎 + 보조 한 줄(선택).
  - conclusion(결): 한 줄 28자 안팎. 단정 대신 "~가 관건", "~가 다음 관전 포인트".
  - date: "MM.DD HH:MM" (기사 시각, KST). source: 확인한 매체 2곳.
- spec을 `alerts/<YYYY-MM-DD>/<HHMM>_<영문슬러그>.json`으로 저장 →
  `python3 generator/cards_v2.py <spec.json> alerts/<YYYY-MM-DD>/<HHMM>_<슬러그>.jpg`
- 만든 jpg를 **Read로 직접 열어** 글자 잘림·겹침·줄바꿈 이상·숫자 오타를 확인. 문제 있으면 문구를 줄여 다시 만든다.

## 5. 캡션(줄글) 쓰기 → 같은 이름의 `.txt`
- 첫 줄: 125자 이내, 다음 줄이 궁금해지게. 인사·해시태그·이미지 설명으로 시작하지 않는다.
- 본문: 3~6줄. 무슨 일 → 왜 중요한지 → 다음에 볼 것. '~다' 체.
- 행동 유도 **1개만**: 해설형은 공유("이거 궁금해하던 사람에게 보내기"), 일정·시리즈형은 팔로우("장 끝나면 매일 정리한다").
- 마지막 줄 "정보 제공 목적이며 투자 권유가 아닙니다." + 해시태그 3~5개.

## 6. 기록·저장
- `state.json`: `last_run_at`을 이번 실행 시각(KST ISO)으로, 알림 보낸 기사 링크를 `alerted_links`에 추가(최근 500개만 유지),
  `alerts`에 {time, title, files, sources} 추가(최근 100개만), 건너뛴 건 `skipped`에 이유와 함께(최근 100개만).
- `git add data/alerts alerts` → 커밋 "알림: <요약> [skip ci]" (끝에 Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>) → `git pull --rebase` → push.
  **posts/ 아래 파일은 절대 add 하지 않는다.**

## 7. 사용자에게 알리기 (알림 건이 있을 때만)
1. SendUserFile로 카드 jpg를 보낸다 (status: proactive).
2. SendUserMessage로 캡션 전문을 그대로 붙여 보낸다. 맨 위 한 줄: "📰 <한 줄 요약> · 출처: 매체1·매체2".
3. PushNotification: "<한 줄 요약> — 카드와 캡션 준비됨" (짧게).
- 알림 건이 없으면 기록만 갱신하고 **아무 알림 없이** 끝낸다.
- 작업이 실패하면(뉴스 수집 실패, 렌더 실패, push 실패 등) PushNotification으로 짧게 원인을 알린다. 같은 원인이 3시간 넘게 이어지면 그때만 다시 알린다 (state의 `last_error` 기록 참고).
