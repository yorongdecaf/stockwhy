"""GitHub Actions에서 실행: posts/<id>/ 의 카드뉴스(캐러셀)와 릴스를 인스타그램에 게시
- Instagram API (Instagram 로그인 방식) 공식 콘텐츠 게시 API 사용
- 인스타 서버가 이미지를 가져갈 공개 URL은 jsDelivr CDN(공개 저장소 커밋 기준)으로 만든다
환경변수: IG_ACCESS_TOKEN, IG_USER_ID, GITHUB_REPOSITORY, GITHUB_SHA
사용법: python publisher/publish.py posts/us_2026-10-30 [--dry-run]
"""
import calendar, json, os, sys, time, pathlib, urllib.parse, urllib.request

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

CALLS = {"n": 0}                                   # 이번 실행에서 인스타 API를 부른 횟수 (로그용)
_call = call
def call(method, path, **params):
    CALLS["n"] += 1
    return _call(method, path, **params)

def wait_ready(cid, label, first=10, gap=15, limit=300):
    """컨테이너 처리 완료까지 대기. 호출 수를 줄이려고 처음엔 기다렸다가 확인하고, 이후엔 간격을 점점 늘린다.
    (예전: 바로 확인 + 5~10초 간격 → 게시 1건에 수십 번 호출해 앱 호출 한도(code 4)에 걸림)"""
    time.sleep(first)
    waited = first
    while True:
        st = call("GET", cid, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED": return
        if code in ("ERROR", "EXPIRED"): raise SystemExit(f"{label} 처리 실패: {st}")
        if waited >= limit: raise SystemExit(f"{label} 처리 시간 초과 ({waited}초)")
        time.sleep(gap); waited += gap
        gap = min(gap + 10, 45)

def publish_media(uid, creation_id, caption, media_type):
    """media_publish 호출 → {"id", "permalink"(있으면)}.
    인스타가 게시를 마친 뒤에도 403(code 4 / 2207051)을 돌려주는 경우가 잦아(11/06 이후 거의 매번)
    실패로 끝내기 전에 최근 게시물에서 같은 캡션을 찾아 확인한다. 이때 permalink도 같이 받아 추가 호출을 아낀다."""
    try:
        return call("POST", f"{uid}/media_publish", creation_id=creation_id)
    except SystemExit as err:
        print("⚠️ media_publish 오류 → 실제 게시 여부 확인:", err, flush=True)
        head = caption.split("\n")[0][:40]
        for wait in (20, 40):                       # 확인은 최대 2번, 간격을 두고
            time.sleep(wait)
            try:
                recent = call("GET", f"{uid}/media", fields="id,media_type,caption,timestamp,permalink",
                              limit="5").get("data", [])
            except SystemExit as e2:
                print("최근 게시물 조회 실패:", e2, flush=True); continue
            cutoff = time.time() - 20 * 60            # 최근 20분 안에 올라온 것만 인정
            for m in recent:
                ts = m.get("timestamp", "")
                try: t = calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
                except ValueError: continue
                if (m.get("media_type") == media_type and t >= cutoff
                        and (m.get("caption") or "").startswith(head)):
                    print(f"✅ 오류 응답과 달리 실제로 게시됨 ({media_type}, id={m['id']}) → 계속 진행", flush=True)
                    return {"id": m["id"], "permalink": m.get("permalink")}
        raise err

def permalink_of(pub):
    return pub.get("permalink") or call("GET", pub["id"], fields="permalink").get("permalink")

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
    # 카드 8장을 하나씩 상태 확인하던 것(8번+α 호출)을 없앰: 잠시 기다린 뒤 바로 캐러셀을 만들고,
    # 아직 처리 전이라 거절될 때만 카드 상태를 확인하고 한 번 더 시도한다.
    time.sleep(15)
    kw = dict(media_type="CAROUSEL", children=",".join(children), caption=caption)
    try:
        car = call("POST", f"{uid}/media", **kw)
    except SystemExit as e:
        print("캐러셀 생성 보류 → 카드 처리 상태 확인 후 재시도:", e, flush=True)
        for c in children: wait_ready(c, "카드 이미지", first=0, gap=10, limit=120)
        car = call("POST", f"{uid}/media", **kw)
    wait_ready(car["id"], "캐러셀", first=10, gap=10, limit=120)
    pub = publish_media(uid, car["id"], caption, "CAROUSEL_ALBUM")
    result["carousel_media_id"] = pub["id"]
    result["carousel_url"] = permalink_of(pub)
    print("캐러셀 게시 완료:", result["carousel_url"], flush=True)

def main(folder, dry=False):
    folder = pathlib.Path(folder)
    post = json.loads((folder / "post.json").read_text())
    done = folder / "published.json"
    rec = json.loads(done.read_text()) if done.exists() else {}
    def save():                                   # 단계마다 바로 기록 → 중간에 끊겨도 이어서 진행
        done.write_text(json.dumps(rec, indent=2))
    if not post.get("publish", True):
        print("publish=false, 건너뜀"); return
    need_car = not rec.get("carousel_media_id") and not post.get("skip_carousel")
    need_reel = bool(post.get("reel")) and not rec.get("reel_media_id")
    if not need_car and not need_reel:
        print("인스타 이미 게시됨, 건너뜀:", folder); return
    caption = (folder / "caption.txt").read_text()
    uid = os.environ["IG_USER_ID"]
    urls = [public_url(folder, c) for c in post["cards"]]
    reel_url = public_url(folder, post["reel"]) if post.get("reel") else None
    print("이미지 URL 예:", urls[0], flush=True)
    if dry:
        print("dry-run: 실제 게시 안 함"); return
    for u in urls + ([reel_url] if reel_url else []): warm(u)

    if need_car:
        publish_carousel(uid, urls, caption, rec)
        rec["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z"); save()
    else:
        print("캐러셀 이미 게시됨 → 건너뜀")

    if need_reel:
        rc = call("POST", f"{uid}/media", media_type="REELS", video_url=reel_url, caption=caption,
                  share_to_feed="true" if post.get("reel_share_to_feed") else "false")
        wait_ready(rc["id"], "릴스 영상", first=30, gap=15, limit=600)   # 영상은 처리에 시간이 걸려 처음 30초는 확인 안 함
        rp = publish_media(uid, rc["id"], caption, "VIDEO")
        rec["reel_media_id"] = rp["id"]
        rec["reel_url"] = permalink_of(rp)
        print("릴스 게시 완료:", rec["reel_url"], flush=True)
        save()
    print(f"인스타 API 호출 수: {CALLS['n']}회", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], dry="--dry-run" in sys.argv)
