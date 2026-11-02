"""게시 기록(published.json)에 인스타 게시물 링크(permalink)를 채워 넣는다."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from publish import call

for f in sorted(pathlib.Path("posts").glob("*/published.json")):
    d = json.loads(f.read_text())
    for key in ("carousel_media_id", "reel_media_id"):
        mid = d.get(key)
        lk = key.replace("_media_id", "_url")
        if mid and not d.get(lk):
            d[lk] = call("GET", mid, fields="permalink").get("permalink")
    f.write_text(json.dumps(d, indent=2))
    print(f.parent.name, "| 카드뉴스:", d.get("carousel_url"), "| 릴스:", d.get("reel_url"))
