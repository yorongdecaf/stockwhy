"""GitHub Actions에서 실행: posts/<id>/ 의 카드뉴스(캐러셀)와 릴스를 인스타그램에 게시
- Instagram API (Instagram 로그인 방식) 공식 콘텐츠 게시 API 사용
- 인스타 서버가 이미지를 가져갈 공개 URL은 jsDelivr CDN(공개 저장소 커밋 기준)으로 만든다
환경변수: IG_ACCESS_TOKEN, IG_USER_ID, GITHUB_REPOSITORY, GITHUB_SHA
사용법: python publisher/publish.py posts/us_2026-10-30 [--dry-run]
"""
import json, os, sys, time, pathlib, urllib.parse, urllib.request

# 토큰 종류에 따라 접속 주소 자동 선택
#  - EAA... : 페이스북(통합 로그인/시스템 사용자) 토큰 → graph.facebook.com
#  - IG...  : 인스타그램 로그인 토큰 → graph.instagram.com
_TOK = os.environ.get("IG_ACCESS_TOKEN", "")
HOST = "graph.instagram.com" if _TOK.startswith("IG") else "graph.facebook.com"
API = f"https://{HOST}/" + os.environ.get("IG_API_VERSION", "v23.0")

def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"API 오류 {e.code} ({path}): {body}")

def wait_ready(cid, label, tries=30, gap=10):
    for _ in range(tries):
        st = call("GET", cid, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED": return
        if code in ("ERROR", "EXPIRED"): raise SystemExit(f"{label} 처리 실패: {st}")
        time.sleep(gap)
    raise SystemExit(f"{label} 처리 시간 초과")

def public_url(folder, name):
    repo, sha = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    return f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{folder.as_posix()}/{name}"

def warm(url):
    """jsDelivr가 파일을 미리 캐시하도록 한 번 요청 (인스타가 가져갈 때 지연 방지)"""
    try: urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60)
    except Exception as e: print("warm 실패(무시):", url, e)

def publish_carousel(uid, urls, caption, result):
    children = []
    for u in urls:
        c = call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")
        children.append(c["id"])
    for c in children: wait_ready(c, "카드 이미지", tries=12, gap=5)
    car = call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)
    wait_ready(car["id"], "캐러셀", tries=12, gap=5)
    pub = call("POST", f"{uid}/media_publish", creation_id=car["id"])
    result["carousel_media_id"] = pub["id"]
    result["carousel_url"] = call("GET", pub["id"], fields="permalink").get("permalink")
    print("캐러셀 게시 완료:", result["carousel_url"])

def main(folder, dry=False):
    folder = pathlib.Path(folder)
    post = json.loads((folder / "post.json").read_text())
    done = folder / "published.json"
    if done.exists():
        print("이미 게시됨, 건너뜀:", folder); return
    if not post.get("publish", True):
        print("publish=false, 건너뜀"); return
    caption = (folder / "caption.txt").read_text()
    uid = os.environ["IG_USER_ID"]
    urls = [public_url(folder, c) for c in post["cards"]]
    reel_url = public_url(folder, post["reel"]) if post.get("reel") else None
    print("이미지 URL 예:", urls[0])
    if dry:
        print("dry-run: 실제 게시 안 함"); return
    for u in urls + ([reel_url] if reel_url else []): warm(u)

    result = {}
    # 1) 카드뉴스 캐러셀 (post.json에 skip_carousel=true면 건너뜀: 캐러셀만 먼저 올라간 경우 릴스만 보충 게시)
    if not post.get("skip_carousel"):
        publish_carousel(uid, urls, caption, result)
    else:
        print("skip_carousel=true → 캐러셀 건너뜀")

    # 2) 릴스 (무음 영상)
    if reel_url:
        rc = call("POST", f"{uid}/media", media_type="REELS", video_url=reel_url, caption=caption,
                  share_to_feed="true" if post.get("reel_share_to_feed") else "false")
        wait_ready(rc["id"], "릴스 영상")
        rp = call("POST", f"{uid}/media_publish", creation_id=rc["id"])
        result["reel_media_id"] = rp["id"]
        result["reel_url"] = call("GET", rp["id"], fields="permalink").get("permalink")
        print("릴스 게시 완료:", result["reel_url"])

    result["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    done.write_text(json.dumps(result, indent=2))

if __name__ == "__main__":
    main(sys.argv[1], dry="--dry-run" in sys.argv)
