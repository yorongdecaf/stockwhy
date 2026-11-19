# 알림 카드 보관함

매시간 예약 작업이 중요한 뉴스를 골라 만든 카드(jpg)와 캡션(txt)이 날짜별로 쌓인다.
- 생성기: `generator/cards_v2.py` (템플릿: number · quote · ranking · calendar · flash)
- 중복 방지 기록: `data/alerts/state.json`
- ⚠️ 이 폴더는 자동 게시와 무관하다. 게시는 사람이 인스타 앱에서 직접 한다.
