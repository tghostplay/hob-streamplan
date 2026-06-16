#!/usr/bin/env python3
"""
Baut eine statische Website aus den neuesten Posts eines Subreddits.
Gedacht fuer r/HandOfMemes, um den "Streamplan" anzuzeigen (Discord-Ersatz).

Datenquelle: Reddit (oeffentlich, erlaubt).
- Wenn REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET gesetzt sind, wird die
  offizielle OAuth-API genutzt (zuverlaessig, auch in GitHub Actions).
- Sonst wird der oeffentliche .json-Endpunkt genutzt (gut zum lokalen Testen).
"""

import os
import sys
import html
import json
import datetime as dt

import requests

# ----------------------------------------------------------------------------
# KONFIGURATION  --  hier anpassen
# ----------------------------------------------------------------------------
SUBREDDIT = "HandOfMemes"          # ohne "r/"
FLAIR_FILTER = "streamplan"        # nur Posts mit diesem Flair; "" = alle Posts
MAX_POSTS = 5                      # so viele Posts maximal anzeigen
FETCH_LIMIT = 30                  # so viele Posts von Reddit holen (zum Filtern)
SITE_TITLE = "HandOfMemes \u2013 Streamplan"
SITE_SUBTITLE = "Automatisch aus r/HandOfMemes \u00fcbernommen"
AUTO_RELOAD_MINUTES = 15           # offene Seite laedt sich so oft neu (0 = aus)
OUTPUT_DIR = "public"
# ----------------------------------------------------------------------------

USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT",
    "streamplan-mirror/1.0 (static site builder)",
)


def fetch_posts():
    """Holt die neuesten Posts. OAuth wenn moeglich, sonst public JSON."""
    cid = os.environ.get("REDDIT_CLIENT_ID")
    csecret = os.environ.get("REDDIT_CLIENT_SECRET")

    if cid and csecret:
        # --- Offizielle, zuverlaessige OAuth-Variante (application-only) ---
        token_res = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=requests.auth.HTTPBasicAuth(cid, csecret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        token_res.raise_for_status()
        token = token_res.json()["access_token"]
        res = requests.get(
            f"https://oauth.reddit.com/r/{SUBREDDIT}/new",
            params={"limit": FETCH_LIMIT, "raw_json": 1},
            headers={"Authorization": f"bearer {token}", "User-Agent": USER_AGENT},
            timeout=30,
        )
    else:
        # --- Oeffentlicher Endpunkt (gut lokal; in CI evtl. geblockt) ---
        res = requests.get(
            f"https://www.reddit.com/r/{SUBREDDIT}/new.json",
            params={"limit": FETCH_LIMIT, "raw_json": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )

    res.raise_for_status()
    children = res.json()["data"]["children"]
    return [c["data"] for c in children]


def extract_images(post):
    """Findet Bild-URLs in einem Post (Einzelbild oder Galerie)."""
    urls = []

    url = post.get("url_overridden_by_dest") or post.get("url") or ""
    base = url.lower().split("?")[0]
    is_image = (
        base.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
        or "i.redd.it" in url
        or post.get("post_hint") == "image"
    )
    if is_image and url:
        urls.append(url)

    # Vorschaubild als Rueckfall
    if not urls:
        try:
            src = post["preview"]["images"][0]["source"]["url"]
            urls.append(html.unescape(src))
        except (KeyError, IndexError, TypeError):
            pass

    # Galerie (mehrere Bilder)
    if post.get("is_gallery") and post.get("media_metadata"):
        urls = []
        order = [it["media_id"] for it in post.get("gallery_data", {}).get("items", [])]
        for mid in order:
            meta = post["media_metadata"].get(mid, {})
            src = meta.get("s", {}).get("u")
            if src:
                urls.append(html.unescape(src))

    return urls


def humanize_age(created_utc):
    delta = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromtimestamp(
        created_utc, dt.timezone.utc
    )
    secs = int(delta.total_seconds())
    if secs < 3600:
        return f"vor {max(1, secs // 60)} Min."
    if secs < 86400:
        return f"vor {secs // 3600} Std."
    return f"vor {secs // 86400} Tg."


def select_posts(posts):
    if FLAIR_FILTER:
        f = FLAIR_FILTER.lower()
        filtered = [
            p for p in posts
            if f in (p.get("link_flair_text") or "").lower()
        ]
        if filtered:
            posts = filtered
    return posts[:MAX_POSTS]


def render_post_card(post, is_first):
    title = html.escape(post.get("title", "(ohne Titel)"))
    created = post.get("created_utc", 0)
    date_str = dt.datetime.fromtimestamp(created, dt.timezone.utc).strftime(
        "%d.%m.%Y"
    )
    age = humanize_age(created)
    permalink = "https://reddit.com" + post.get("permalink", "")
    author = html.escape(post.get("author", "?"))

    body = ""
    selftext_html = post.get("selftext_html")
    if selftext_html:
        body = html.unescape(selftext_html)

    images_html = ""
    for img in extract_images(post):
        images_html += (
            f'<img class="post-img" src="{html.escape(img)}" '
            f'alt="" loading="lazy">'
        )

    new_badge = '<span class="badge">neu</span>' if is_first else ""

    flair = post.get("link_flair_text") or ""
    flair_html = (
        f'<span class="flair">{html.escape(flair)}</span>' if flair else ""
    )

    return f"""
      <article class="card{' card--first' if is_first else ''}">
        <div class="card-eyebrow">
          <span class="dot"></span>{date_str}
          <span class="sep">/</span>{age}
          <span class="sep">/</span>u/{author}
          {new_badge}
        </div>
        <h2 class="card-title">{title}</h2>
        {flair_html}
        <div class="card-body">{body}{images_html}</div>
        <a class="card-link" href="{html.escape(permalink)}" target="_blank"
           rel="noopener">Auf Reddit ansehen \u2192</a>
      </article>
    """


def render_html(posts):
    now = dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y, %H:%M UTC")
    cards = "".join(
        render_post_card(p, i == 0) for i, p in enumerate(posts)
    )
    if not posts:
        cards = (
            '<div class="empty">Noch keine passenden Posts gefunden. '
            "Sobald ein neuer Streamplan im Subreddit erscheint, taucht er hier auf.</div>"
        )

    reload_meta = (
        f'<meta http-equiv="refresh" content="{AUTO_RELOAD_MINUTES * 60}">'
        if AUTO_RELOAD_MINUTES
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{reload_meta}
<title>{html.escape(SITE_TITLE)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #15131f;
    --bg-2: #1d1930;
    --card: #221d3a;
    --card-edge: #322a52;
    --ink: #ECEAF5;
    --muted: #9b97b8;
    --accent: #FF8A5B;
    --accent-2: #8b86f0;
    --live: #4ade80;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0;
    background:
      radial-gradient(1100px 600px at 80% -10%, #2a2350 0%, transparent 60%),
      radial-gradient(900px 500px at -10% 10%, #241d3f 0%, transparent 55%),
      var(--bg);
    color: var(--ink);
    font-family: "Inter", system-ui, sans-serif;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 760px; margin: 0 auto; padding: 56px 22px 90px; }}

  header {{ margin-bottom: 40px; }}
  .kicker {{
    font-family: "JetBrains Mono", monospace;
    font-size: 12px; letter-spacing: .14em; text-transform: uppercase;
    color: var(--muted); display: flex; align-items: center; gap: 9px;
  }}
  .live-dot {{
    width: 8px; height: 8px; border-radius: 50%; background: var(--live);
    box-shadow: 0 0 0 0 rgba(74,222,128,.6); animation: pulse 2.4s infinite;
  }}
  @keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(74,222,128,.55); }}
    70% {{ box-shadow: 0 0 0 10px rgba(74,222,128,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(74,222,128,0); }}
  }}
  h1 {{
    font-family: "Bricolage Grotesque", sans-serif;
    font-weight: 800; font-size: clamp(34px, 7vw, 56px);
    line-height: 1.02; letter-spacing: -.02em; margin: 14px 0 8px;
    background: linear-gradient(100deg, var(--ink) 30%, var(--accent) 130%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }}
  .subtitle {{ color: var(--muted); font-size: 15px; margin: 0; }}
  .updated {{
    font-family: "JetBrains Mono", monospace; font-size: 12px;
    color: var(--muted); margin-top: 18px;
  }}
  .updated b {{ color: var(--accent-2); font-weight: 500; }}

  .card {{
    background: linear-gradient(180deg, var(--card) 0%, var(--bg-2) 100%);
    border: 1px solid var(--card-edge);
    border-radius: 18px; padding: 26px 26px 22px; margin-bottom: 22px;
    position: relative; overflow: hidden;
  }}
  .card--first {{ border-color: rgba(255,138,91,.45); }}
  .card--first::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    background: linear-gradient(var(--accent), var(--accent-2));
  }}
  .card-eyebrow {{
    font-family: "JetBrains Mono", monospace; font-size: 12px;
    color: var(--muted); display: flex; align-items: center;
    gap: 8px; flex-wrap: wrap; margin-bottom: 12px;
  }}
  .card-eyebrow .dot {{
    width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
  }}
  .card-eyebrow .sep {{ opacity: .4; }}
  .badge {{
    margin-left: auto; background: rgba(255,138,91,.16); color: var(--accent);
    border: 1px solid rgba(255,138,91,.4); padding: 1px 9px; border-radius: 99px;
    font-size: 11px; letter-spacing: .06em; text-transform: uppercase;
  }}
  .card-title {{
    font-family: "Bricolage Grotesque", sans-serif; font-weight: 700;
    font-size: clamp(20px, 3.4vw, 26px); line-height: 1.2;
    letter-spacing: -.01em; margin: 0 0 10px;
  }}
  .flair {{
    display: inline-block; margin: 0 0 14px; padding: 2px 11px;
    background: #2a2347; border: 1px solid var(--card-edge); border-radius: 99px;
    font-family: "JetBrains Mono", monospace; font-size: 11px;
    letter-spacing: .04em; color: var(--accent-2);
  }}
  .card-body {{ color: #d7d3ea; font-size: 15.5px; }}
  .card-body p {{ margin: 0 0 12px; }}
  .card-body a {{ color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }}
  .card-body h1, .card-body h2, .card-body h3 {{
    font-family: "Bricolage Grotesque", sans-serif; margin: 18px 0 8px;
    font-size: 18px;
  }}
  .card-body ul, .card-body ol {{ margin: 0 0 12px; padding-left: 20px; }}
  .card-body li {{ margin: 3px 0; }}
  .card-body blockquote {{
    margin: 0 0 12px; padding: 6px 14px; border-left: 3px solid var(--accent-2);
    color: var(--muted);
  }}
  .card-body code {{
    background: #0f0d18; padding: 1px 6px; border-radius: 5px;
    font-family: "JetBrains Mono", monospace; font-size: 13px;
  }}
  .card-body table {{ border-collapse: collapse; width: 100%; margin: 0 0 12px; font-size: 14px; }}
  .card-body th, .card-body td {{
    border: 1px solid var(--card-edge); padding: 7px 10px; text-align: left;
  }}
  .card-body th {{ background: #2a2347; }}
  .post-img {{
    display: block; max-width: 100%; height: auto; border-radius: 12px;
    margin: 14px 0 4px; border: 1px solid var(--card-edge);
  }}
  .card-link {{
    display: inline-block; margin-top: 14px; color: var(--accent-2);
    font-size: 13px; font-weight: 600; text-decoration: none;
  }}
  .card-link:hover {{ color: var(--accent); }}

  .empty {{
    text-align: center; color: var(--muted); padding: 60px 20px;
    border: 1px dashed var(--card-edge); border-radius: 18px;
  }}

  footer {{
    margin-top: 40px; padding-top: 22px; border-top: 1px solid var(--card-edge);
    color: var(--muted); font-size: 13px; text-align: center;
  }}
  footer a {{ color: var(--accent-2); }}

  @media (prefers-reduced-motion: reduce) {{
    .live-dot {{ animation: none; }}
    html {{ scroll-behavior: auto; }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="kicker"><span class="live-dot"></span>Stream-Plan</div>
      <h1>{html.escape(SITE_TITLE)}</h1>
      <p class="subtitle">{html.escape(SITE_SUBTITLE)}</p>
      <p class="updated">Zuletzt aktualisiert: <b>{now}</b></p>
    </header>

    <main>
      {cards}
    </main>

    <footer>
      Quelle: <a href="https://reddit.com/r/{SUBREDDIT}" target="_blank"
      rel="noopener">r/{SUBREDDIT}</a> &middot; aktualisiert sich automatisch
    </footer>
  </div>
</body>
</html>"""


def main():
    posts = fetch_posts()
    selected = select_posts(posts)
    page = render_html(selected)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"OK: {len(selected)} Post(s) gerendert -> {out}")


if __name__ == "__main__":
    main()
