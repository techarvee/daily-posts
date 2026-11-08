"""Publish the next unpublished post to Instagram (carousel) and Facebook page (multi-photo).

Needs env vars (set as GitHub Actions secrets):
  META_ACCESS_TOKEN  long-lived Page access token
  FB_PAGE_ID         Facebook page id
  IG_USER_ID         Instagram business account id linked to the page
Optional: GRAPH_VERSION (default v21.0), DRY_RUN=1

State is kept in state.json (list of published post ids).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "techarvee/daily-posts")
BRANCH = os.environ.get("BRANCH", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/posts"
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v21.0')}"

HASHTAGS = {
    "Instagram Growth": "#instagramgrowth #instagramtips #contentcreator #reelsindia #socialmediatips",
    "YouTube Growth": "#youtubegrowth #youtubetips #youtuberindia #contentcreator #shorts",
    "Facebook Growth": "#facebookgrowth #facebooktips #socialmediamarketing #contentcreator #facebookreels",
    "Digital Products": "#digitalproducts #onlinebusiness #passiveincome #earnonline #canva",
    "Organic Selling": "#organicmarketing #digitalproducts #onlinebusiness #instagrammarketing #sellonline",
    "Content Ideas": "#contentideas #contentcreator #instagramtips #reelsindia #creatortips",
    "Mindset": "#creatormindset #motivation #onlinebusiness #contentcreator #growthmindset",
}


def all_posts():
    posts = []
    for cf in sorted((ROOT / "content").glob("*.json")):
        posts += json.loads(cf.read_text(encoding="utf-8"))
    return posts


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"published": []}


def api(path, params, method="POST"):
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        url += "?" + data.decode()
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Graph API error on {path}: {e.read().decode()}") from None


def wait_ready(container_id, token):
    for _ in range(30):
        st = api(container_id, {"fields": "status_code", "access_token": token}, "GET")
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"IG container {container_id} failed: {st}")
        time.sleep(5)
    raise RuntimeError(f"IG container {container_id} not ready in time")


def publish_instagram(urls, caption, ig_user, token):
    children = []
    for u in urls:
        c = api(f"{ig_user}/media", {"image_url": u, "is_carousel_item": "true", "access_token": token})
        children.append(c["id"])
    for c in children:
        wait_ready(c, token)
    car = api(f"{ig_user}/media", {
        "media_type": "CAROUSEL", "children": ",".join(children),
        "caption": caption, "access_token": token})
    wait_ready(car["id"], token)
    res = api(f"{ig_user}/media_publish", {"creation_id": car["id"], "access_token": token})
    return res["id"]


def publish_facebook(urls, caption, page_id, token):
    ids = []
    for u in urls:
        p = api(f"{page_id}/photos", {"url": u, "published": "false", "access_token": token})
        ids.append(p["id"])
    params = {"message": caption, "access_token": token}
    for i, pid in enumerate(ids):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    res = api(f"{page_id}/feed", params)
    return res["id"]


def main():
    state = load_state()
    done = set(state["published"])
    nxt = next((p for p in all_posts() if p["id"] not in done), None)
    if not nxt:
        print("::warning::Content bank khatam! content/ mein naye posts add karo.")
        return
    imgs = sorted((ROOT / "posts" / nxt["id"]).glob("*.jpg"))
    urls = [f"{RAW}/{nxt['id']}/{f.name}" for f in imgs]
    caption = f"{nxt['title']}\n\n{nxt.get('caption', '')}\n\nFollow @ravidigitalproduct for more 🚀\n\n{HASHTAGS.get(nxt.get('tag'), '')}"
    print("Next post:", nxt["id"], "-", nxt["title"], f"({len(urls)} slides)")

    token = os.environ.get("META_ACCESS_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    ig_user = os.environ.get("IG_USER_ID")
    if os.environ.get("DRY_RUN") == "1" or not token:
        print("::notice::DRY RUN (META_ACCESS_TOKEN set nahi hai) - kuch publish nahi hua.")
        for u in urls:
            print(" ", u)
        return

    results, errors = {}, []
    if ig_user:
        try:
            results["instagram"] = publish_instagram(urls, caption, ig_user, token)
        except Exception as e:  # keep going to Facebook
            errors.append(f"Instagram: {e}")
    if page_id:
        try:
            results["facebook"] = publish_facebook(urls, caption, page_id, token)
        except Exception as e:
            errors.append(f"Facebook: {e}")
    print("Published:", results)
    if results:
        state["published"].append(nxt["id"])
        state.setdefault("log", []).append({"id": nxt["id"], "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), **results})
        STATE.write_text(json.dumps(state, indent=2))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
