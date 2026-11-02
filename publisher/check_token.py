"""토큰 확인 + 갱신 (60일 만료 토큰을 연장)
- 계정 정보를 조회해 토큰이 살아있는지 확인하고
- refresh_access_token으로 만료일을 다시 60일로 늘린다.
  (새 토큰 문자열이 다르면 GH_PAT가 있을 때 GitHub Secret을 자동 교체)
"""
import json, os, subprocess, urllib.parse, urllib.request

tok = os.environ["IG_ACCESS_TOKEN"]

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r: return json.loads(r.read())

me = get("https://graph.instagram.com/me?" + urllib.parse.urlencode(
    {"fields": "user_id,username,account_type", "access_token": tok}))
print("연결된 계정:", me.get("username"), "| 유형:", me.get("account_type"), "| user_id:", me.get("user_id"))

r = get("https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": tok}))
days = int(r.get("expires_in", 0)) // 86400
print(f"토큰 갱신 완료: 앞으로 약 {days}일 유효")
new = r.get("access_token")
if new and new != tok:
    if os.environ.get("GH_TOKEN"):
        subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN", "--body", new], check=True)
        print("새 토큰을 GitHub Secret에 저장했습니다.")
    else:
        print("⚠️ 새 토큰이 발급됐지만 GH_PAT가 없어 Secret을 교체하지 못했습니다.")
