"""posts/<id>/ 의 카드뉴스를 스레드(Threads)에 캐러셀로 게시
환경변수: THREADS_ACCESS_TOKEN, THREADS_USER_ID, GITHUB_REPOSITORY, GITHUB_SHA
- 스레드 본문은 500자 제한 → threads.txt (없으면 caption.txt 앞부분)
- 게시 기록은 published.json 의 threads_* 키로 남겨 중복 게시 방지
사용법: python publisher/threads.py posts/us_2026-10-30
"""
import datetime, json, os, sys, time, pathlib, urllib.parse, urllib.request

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

def publish_container(uid, cid):
    for attempt in range(4):                       # "Media Not Found"(아직 반영 전)면 잠시 후 재시도
        try:
            return call("POST", f"{uid}/threads_publish", creation_id=cid)
        except SystemExit as e:
            if "4279009" in str(e) and attempt < 3:
                print("컨테이너 반영 대기 후 재시도...", flush=True); time.sleep(30); continue
            raise

def affiliate_text(folder):
    """data/affiliate.json 에서 이번 게시물에 붙일 쿠팡 링크 댓글 본문을 만든다 (없으면 None)"""
    cfg_path = pathlib.Path(__file__).resolve().parent.parent / "data" / "affiliate.json"
    if not cfg_path.exists(): return None
    cfg = json.loads(cfg_path.read_text())
    if not cfg.get("enabled"): return None
    market = folder.name.split("_")[0]           # kr / us / term
    items = [i for i in cfg.get("items", []) if i.get("url") and i.get("market", "all") in ("all", market)]
    if not items: return None
    n = max(1, min(int(cfg.get("per_post", 2)), 5, len(items)))   # 스레드 링크 5개 제한
    try:                                                          # 날짜마다 돌아가며 노출
        start = datetime.date.fromisoformat(folder.name.split("_")[-1]).toordinal() * n % len(items)
    except ValueError:
        start = sum(map(ord, folder.name)) % len(items)
    pick = [items[(start + k) % len(items)] for k in range(n)]
    lines = [cfg["disclosure"], "", cfg.get("heading", "추천템")]  # 대가성 문구는 반드시 첫 줄
    for i in pick:
        lines += [f"• {i['title']}", i["url"]]
    return "\n".join(lines)[:500]

def post_affiliate_reply(uid, folder, rec, rec_path):
    if rec.get("threads_reply_id") or not rec.get("threads_media_id"): return
    text = affiliate_text(folder)
    if not text:
        print("쿠팡 링크 없음 → 댓글 건너뜀"); return
    try:
        c = call("POST", f"{uid}/threads", media_type="TEXT", text=text, reply_to_id=rec["threads_media_id"])
        wait_ready(c["id"], "쿠팡 링크 댓글")
        time.sleep(10)
        r = publish_container(uid, c["id"])
    except SystemExit as e:                        # 댓글 실패가 본 게시물 기록을 망치지 않게
        print("⚠️ 쿠팡 링크 댓글 실패 (threads_manage_replies 권한 확인):", e, flush=True); return
    rec["threads_reply_id"] = r["id"]
    rec_path.write_text(json.dumps(rec, indent=2))
    print("쿠팡 링크 댓글 완료:", r["id"], flush=True)

def main(folder):
    folder = pathlib.Path(folder)
    if not os.environ.get("THREADS_ACCESS_TOKEN"):
        print("THREADS_ACCESS_TOKEN 없음 → 스레드 건너뜀"); return
    post = json.loads((folder / "post.json").read_text())
    rec_path = folder / "published.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    uid = os.environ.get("THREADS_USER_ID") or "me"
    if rec.get("threads_media_id"):
        print("스레드 이미 게시됨")
        post_affiliate_reply(uid, folder, rec, rec_path); return
    tp = folder / "threads.txt"
    text = tp.read_text() if tp.exists() else (folder / "caption.txt").read_text()
    text = text[:500]
    kids = []
    for c in post["cards"]:
        r = call("POST", f"{uid}/threads", media_type="IMAGE", image_url=public_url(folder, c), is_carousel_item="true")
        kids.append(r["id"])
    for k in kids: wait_ready(k, "스레드 이미지")
    car = call("POST", f"{uid}/threads", media_type="CAROUSEL", children=",".join(kids), text=text)
    wait_ready(car["id"], "스레드 캐러셀")
    time.sleep(30)                                 # Meta 권장: 게시 전 약 30초 대기
    pub = publish_container(uid, car["id"])
    rec["threads_media_id"] = pub["id"]
    rec["threads_url"] = call("GET", pub["id"], fields="permalink").get("permalink")
    rec_path.write_text(json.dumps(rec, indent=2))
    print("스레드 게시 완료:", rec["threads_url"], flush=True)
    post_affiliate_reply(uid, folder, rec, rec_path)

if __name__ == "__main__":
    main(sys.argv[1])
