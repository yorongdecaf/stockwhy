"""토큰 점검 (게시 없이 연결만 확인)
- 시스템 사용자 토큰(EAA...): 만료 없음 → 계정 조회 + 게시 한도 확인
- 인스타그램 로그인 토큰(IG...): 계정 조회 + 60일 연장(refresh)
"""
import json, os, subprocess, urllib.parse, urllib.request

tok = os.environ["IG_ACCESS_TOKEN"]
uid = os.environ.get("IG_USER_ID", "")

def get(url, **q):
    q["access_token"] = tok
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(q), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"오류 {e.code}: {e.read().decode(errors='replace')}")

if tok.startswith("IG"):
    base = "https://graph.instagram.com"
    me = get(f"{base}/me", fields="user_id,username,account_type")
    print("연결된 계정:", me.get("username"), "| 유형:", me.get("account_type"), "| user_id:", me.get("user_id"))
    r = get(f"{base}/refresh_access_token", grant_type="ig_refresh_token")
    print(f"토큰 연장 완료: 약 {int(r.get('expires_in', 0)) // 86400}일 유효")
    new = r.get("access_token")
    if new and new != tok and os.environ.get("GH_TOKEN"):
        subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN", "--body", new], check=True)
        print("새 토큰을 GitHub Secret에 저장했습니다.")
else:
    base = "https://graph.facebook.com/v23.0"
    acct = get(f"{base}/{uid}", fields="username,name,followers_count,media_count")
    print("연결된 계정:", acct.get("username"), "| 팔로워:", acct.get("followers_count"), "| 게시물:", acct.get("media_count"))
    lim = get(f"{base}/{uid}/content_publishing_limit", fields="quota_usage,config")
    print("최근 24시간 API 게시 사용량:", json.dumps(lim.get("data", lim), ensure_ascii=False))
    # 게시 한도 조회가 성공했다면 instagram_content_publish 권한이 있는 것
    print("게시 권한: 확인됨 (content_publishing_limit 조회 성공)")
print("✅ 토큰 점검 통과")
