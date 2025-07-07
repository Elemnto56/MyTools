#!/usr/bin/env python3
import argparse
import random
import requests
import shutil
import subprocess
import os

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers   import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# ─── CONFIG ────────────────────────────────────────────────────────────────
SUBREDDITS       = [
    "AskReddit",
    "NoStupidQuestions",
    "TIFU",
    "TrueOffMyChest",
    "ChangeMyView",
    "relationships",
    "Showerthoughts",
    "LifeProTips",
    "AskHistorians",
    "AskScience",
    "CasualConversation",
]
HEADERS          = {"User-Agent": "IntextSumyViewer/1.0"}
FETCH_LIMIT      = 100
SUMMARY_SENTENCES= 5
USE_CHAFA        = shutil.which("chafa") is not None
# ────────────────────────────────────────────────────────────────────────────

def quick_summary(text: str, sentences: int = SUMMARY_SENTENCES) -> str:
    parser     = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = TextRankSummarizer()
    return "\n".join(str(s) for s in summarizer(parser.document, sentences))

def fetch_hot_posts(subreddit: str) -> list:
    """Fetch up to FETCH_LIMIT hot posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={FETCH_LIMIT}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [child["data"] for child in r.json()["data"]["children"]]

def pick_random_post(posts: list, text_only: bool) -> dict:
    """Filter & return one random post from the list (or None)."""
    candidates = []
    for p in posts:
        if p.get("stickied") or p.get("over_18"):
            continue
        body   = p.get("selftext","").strip()
        url    = p.get("url","")
        is_img = any(url.lower().endswith(ext) for ext in (".jpg",".jpeg",".png",".gif"))
        if text_only:
            if not body or is_img:
                continue
        candidates.append(p)
    return random.choice(candidates) if candidates else None

def render_image(path: str):
    if USE_CHAFA:
        subprocess.run(["chafa","--symbols=block","--size=60x30",path])
    else:
        print(f"[Image] {path}")

def download_image(url: str) -> str:
    tmp = "tmp_img.dat"
    r = requests.get(url, headers=HEADERS, stream=True, timeout=10)
    r.raise_for_status()
    with open(tmp,"wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)
    return tmp

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--textonly", action="store_true", help="Only posts with text bodies")
    p.add_argument("--summarize",action="store_true", help=f"Extract top {SUMMARY_SENTENCES} sentences")
    args = p.parse_args()

    # Shuffle subs so we don't always start with the same one
    subs = SUBREDDITS[:]
    random.shuffle(subs)

    for sub in subs:
        try:
            posts = fetch_hot_posts(sub)
        except Exception as e:
            continue

        post = pick_random_post(posts, text_only=args.textonly)
        if not post:
            continue

        # Show it
        print(f"\n r/{sub}")
        print("Title:", post.get("title","[no title]"), "\n")

        body = post.get("selftext","").strip()
        if body:
            if args.summarize:
                print("Summary:")
                print(quick_summary(body), "\n")
            else:
                print(body, "\n")
        else:
            print("(no text body)\n")

        if not args.textonly:
            url = post.get("url","")
            if any(url.lower().endswith(ext) for ext in (".jpg",".jpeg",".png",".gif")):
                try:
                    img = download_image(url)
                    print("🖼 Rendering image...\n")
                    render_image(img)
                    os.remove(img)
                except:
                    print(f"[Image] {url}\n")

        print("LINK: https://reddit.com" + post.get("permalink",""))
        return

    print("No suitable post found in any subreddit.")

if __name__=="__main__":
    main()

