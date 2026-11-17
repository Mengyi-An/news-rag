"""
Fetch news from a few RSS feeds, save articles every day at the fixed time. 
Then fetch_news as an retrieval augmentation for my news agent.

Usage:
    python -m src.fetch_news
"""

import re # 正则表达式
import html # 处理 HTML 里的特殊符号
import feedparser   # 用来读 RSS 的库
import json 
import os

feeds = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "BBC Sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "NPR News": "https://feeds.npr.org/1001/rss.xml",
}


def clean_text(text):
    """
    function: turn an RSS summary into plain text
        some feeds put HTML tags, entities like &amp; and invisible

    output: convert "<p>Prices rose &amp; fell</p>" to "Prices rose & fell" (the special symbols and extra blank space are removed)
    """
    text = re.sub(r"<[^>]+>", " ", text)              # drop HTML tags
    text = html.unescape(text)                         # &amp; -> &
    text = re.sub(r"[​-‏⁠]", "", text)  # drop zero-width characters
    return " ".join(text.split())                      # collapse spaces and newlines


def fetch_feed(source, url):
    """
    function: download one feed and keep the fields we need
    output:
        [{"title": ..., "summary": ..., "link": ..., "source": "BBC World", "published": ...}, ...]
    """
    feed = feedparser.parse(url)
    articles = []

    # each entry represent an article
    for entry in feed.entries:
        articles.append({
            "title": clean_text(entry.get("title", "")),
            "summary": clean_text(entry.get("summary", "")),
            "link": entry.get("link", ""),
            "source": source,
            "published": entry.get("published", ""),
        })
    return articles


def fetch_all():
    """
    function: fetch every feed and remove duplicates (like same link or same title)
        a feed that fails to download is skipped, so one broken feed does not stop the rest
    output:
        list of articles, each with an extra "text" field (title + summary) for the model
    """
    articles = []
    seen = set()
    for source, url in feeds.items():
        try:
            feed_articles = fetch_feed(source, url)
        except Exception as e:
            print(f"skip {source}: {e}")
            continue

        for article in feed_articles:
            key_link = article["link"]
            key_title = article["title"].lower()

            # not article["title"], whether the title is empty string
            # Here, we check there conditions:
            # 1. whether title is empty string
            # 2. whether article link is saved in seen already
            # 3. whether article title is saved in seen already
            if not article["title"] or key_link in seen or key_title in seen:
                continue
            seen.add(key_link)
            seen.add(key_title)

            article["text"] = f"{article['title']} {article['summary']}".strip()
            articles.append(article)
        print(f"{source}: {len(feed_articles)} articles")

    print(f"total after removing duplicates: {len(articles)}")
    return articles

def save_articles(articles, path):
    saved_links = set()
    saved_titles = set()

    # load the dataset in path
    if os.path.exists():
        with open(path, "r", encoding = "utf-8") as f:
            for line in f:
                saved_articles = json.loads(line)
                saved_link = saved_articles["link"]
                saved_title = saved_articles["title"]
                
                saved_links.add(saved_link)
                saved_titles.add(saved_title)

    new_articles = []

    for article in articles:
        key_title = article["title"].lower()
        key_link = article["link"]

        if key_link not in saved_links and key_title not in saved_titles:
            new_articles.append(article)

    # save the new_articles as json
    with open(path, "a", encoding = "utf-8") as f:
        for article in new_articles:
            line = json.dumps(article, ensure_ascii=False)
            f.write(line + "\n")

    num_new = len(new_articles)
    num_total = len(saved_links) + num_new
    print(f"the number of saved articles are {num_new}")
    print(f"the number of total articles are {num_total}")
        


if __name__ == "__main__":
    articles = fetch_all()
    save_articles(articles, "data/news.jsonl")
