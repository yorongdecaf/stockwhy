"""posts/<id>/ 의 카드뉴스를 스레드(Threads)에 캐러셀로 게시
환경변수: THREADS_ACCESS_TOKEN, THREADS_USER_ID, GITHUB_REPOSITORY, GITHUB_SHA
- 스레드 본문은 500자 제한 → threads.txt (없으면 caption.txt 앞부분)
- 게시 기록은 published.json 의 threads_* 키로 남겨 중복 게시 방지
사용법: python publisher/threads.py posts/us_2026-10-30
"""
import json, os, sys, time, pathlib, urllib.parse, urllib.request

API = "https://graph.threads.net/v1.0"

def call(method, path, **params):
    params["access_token"] = os.environ["THREADS_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    req = urllib.request.Request(url + "?" + data.decode()) if method == "GET" else \
          urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Threads API 오류 {e.code} ({path}): {e.read().decode(errors='replace')}")

def wait_ready(cid, label, tries=20, gap=6):
    for _ in range(tries):
        st = call("GET", cid, fields="status,error_message")
        s = st.get("status")
        if s in ("FINISHED", "PUBLISHED"): return
        if s in ("ERROR", "EXPIRED"): raise SystemExit(f"{label} 처리 실패: {st}")
        time.sleep(gap)
    raise SystemExit(f"{label} 처리 시간 초과")

def public_url(folder, name):
    repo, sha = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    return f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{folder.as_posix()}/{name}"

def main(folder):
    folder = pathlib.Path(folder)
    if not os.environ.get("THREADS_ACCESS_TOKEN"):
        print("THREADS_ACCESS_TOKEN 없음 → 스레드 건너뜀"); return
    post = json.loads((folder / "post.json").read_text())
    rec_path = folder / "published.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    if rec.get("threads_media_id"):
        print("스레드 이미 게시됨, 건너뜀"); return
    tp = folder / "threads.txt"
    text = tp.read_text() if tp.exists() else (folder / "caption.txt").read_text()
    text = text[:500]
    uid = os.environ.get("THREADS_USER_ID") or "me"   # ID 없으면 토큰 주인(me)으로 게시
    kids = []
    for c in post["cards"]:
        r = call("POST", f"{uid}/threads", media_type="IMAGE", image_url=public_url(folder, c), is_carousel_item="true")
        kids.append(r["id"])
    for k in kids: wait_ready(k, "스레드 이미지")
    car = call("POST", f"{uid}/threads", media_type="CAROUSEL", children=",".join(kids), text=text)
    wait_ready(car["id"], "스레드 캐러셀")
    pub = call("POST", f"{uid}/threads_publish", creation_id=car["id"])
    rec["threads_media_id"] = pub["id"]
    rec["threads_url"] = call("GET", pub["id"], fields="permalink").get("permalink")
    rec_path.write_text(json.dumps(rec, indent=2))
    print("스레드 게시 완료:", rec["threads_url"])

if __name__ == "__main__":
    main(sys.argv[1])
