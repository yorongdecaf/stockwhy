"""게시 기록(published.json)에 인스타 게시물 링크(permalink)를 채워 넣는다."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from publish import call

UID = os.environ["IG_USER_ID"]
recent = call("GET", f"{UID}/media", fields="id,permalink,media_type,caption,timestamp", limit="25").get("data", [])

print("== 최근 게시물 ==")
for m in recent:
    print(m.get("timestamp"), m["media_type"], m.get("permalink"), (m.get("caption") or "").split("\n")[0][:40])
print("==")

def missing(v): return not str(v or "").isdigit()   # "confirmed-by-owner" 같은 수동 기록은 실제 id로 교체

for f in sorted(pathlib.Path("posts").glob("*/published.json")):
    d = json.loads(f.read_text())
    # 기록이 빠진 게시물은 최근 게시물 목록에서 캡션 첫 줄로 찾아 채움
    head = (f.parent / "caption.txt").read_text().split("\n")[0][:40]
    for m in recent:
        if (m.get("caption") or "").startswith(head):
            if m["media_type"] == "CAROUSEL_ALBUM" and missing(d.get("carousel_media_id")):
                d["carousel_media_id"] = m["id"]; d["carousel_url"] = m["permalink"]
            if m["media_type"] == "VIDEO" and missing(d.get("reel_media_id")):
                d["reel_media_id"] = m["id"]; d["reel_url"] = m["permalink"]
    for key in ("carousel_media_id", "reel_media_id"):
        mid = d.get(key)
        lk = key.replace("_media_id", "_url")
        if mid and not missing(mid) and not d.get(lk):
            d[lk] = call("GET", mid, fields="permalink").get("permalink")
    f.write_text(json.dumps(d, indent=2))
    print(f.parent.name, "| 카드뉴스:", d.get("carousel_url"), "| 릴스:", d.get("reel_url"))
