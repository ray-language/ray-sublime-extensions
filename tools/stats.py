#!/usr/bin/env python3
"""What people make of each extension, from what GitHub already counts.

    GITHUB_TOKEN=… python3 tools/stats.py [--create]

For every entry:

  downloads  every download of the zips its versions name, when they are
             release assets on GitHub
  stars      the stars of its homepage's repository, when that is on GitHub
  up, down   the 👍 and 👎 on its discussion in this repository — one per
             extension, in "Show and tell", titled with its id; with --create
             a missing one is opened

Written to stats.json, apart from the entries: they are reviewed in pull
requests, these change every day and are nobody's to review.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

from common import ROOT, entries

REPO_OWNER = "ray-language"
REPO_NAME = "ray-sublime-extensions"
CATEGORY = "Show and tell"
API = "https://api.github.com"

RELEASE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/releases/download/([^/]+)/([^/?#]+)$")
REPO = re.compile(r"^https://github\.com/([^/]+)/([^/#?]+)")


def request(url, data=None):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ray-sublime-extensions"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def graphql(query, variables):
    answer = request(API + "/graphql", {"query": query, "variables": variables})
    if answer.get("errors"):
        raise RuntimeError(answer["errors"])
    return answer["data"]


def downloads(e, releases):
    total = 0
    for v in e.get("versions", []):
        for a in v.get("artifacts", {}).values():
            m = RELEASE.match(a.get("url", ""))
            if not m:
                continue
            owner, repo, tag, name = m.groups()
            key = (owner, repo, tag)
            if key not in releases:
                try:
                    releases[key] = request(f"{API}/repos/{owner}/{repo}/releases/tags/{tag}")
                except Exception:  # noqa: BLE001 - a missing release counts nothing
                    releases[key] = {"assets": []}
            for asset in releases[key].get("assets", []):
                if asset.get("name") == name:
                    total += asset.get("download_count", 0)
    return total


def stars(e, repos):
    m = REPO.match(e.get("homepage", ""))
    if not m:
        return 0
    key = m.groups()
    if key not in repos:
        try:
            repos[key] = request(f"{API}/repos/{key[0]}/{key[1]}").get("stargazers_count", 0)
        except Exception:  # noqa: BLE001
            repos[key] = 0
    return repos[key]


def discussions():
    """This repository's discussions in the category, by title."""
    q = """query($owner: String!, $name: String!, $after: String) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 25) { nodes { id name } }
        discussions(first: 100, after: $after) {
          pageInfo { hasNextPage endCursor }
          nodes { title url category { name }
            up: reactions(content: THUMBS_UP) { totalCount }
            down: reactions(content: THUMBS_DOWN) { totalCount } }
        }
      }
    }"""
    found, after, repo_id, category_id = {}, None, None, None
    while True:
        data = graphql(q, {"owner": REPO_OWNER, "name": REPO_NAME, "after": after})["repository"]
        repo_id = data["id"]
        for c in data["discussionCategories"]["nodes"]:
            if c["name"] == CATEGORY:
                category_id = c["id"]
        for d in data["discussions"]["nodes"]:
            if d["category"]["name"] == CATEGORY:
                found[d["title"]] = d
        page = data["discussions"]["pageInfo"]
        if not page["hasNextPage"]:
            return found, repo_id, category_id
        after = page["endCursor"]


def open_discussion(repo_id, category_id, e):
    body = (f"**{e.get('name', e['id'])}** — {e.get('description', '')}\n\n"
            "Vote with 👍 or 👎 on this post: ray-sublime shows the count beside the extension. "
            "What worked, what did not, and what you would like are welcome as comments.")
    q = """mutation($repo: ID!, $category: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {repositoryId: $repo, categoryId: $category, title: $title, body: $body}) {
        discussion { title url up: reactions(content: THUMBS_UP) { totalCount }
                     down: reactions(content: THUMBS_DOWN) { totalCount } } } }"""
    return graphql(q, {"repo": repo_id, "category": category_id, "title": e["id"], "body": body})[
        "createDiscussion"]["discussion"]


def main(argv):
    create = "--create" in argv
    releases, repos = {}, {}
    found, repo_id, category_id = discussions()
    out = {}
    for _name, e in entries():
        d = found.get(e["id"])
        if d is None and create and category_id:
            d = open_discussion(repo_id, category_id, e)
        out[e["id"]] = {
            "downloads": downloads(e, releases),
            "stars": stars(e, repos),
            "up": d["up"]["totalCount"] if d else 0,
            "down": d["down"]["totalCount"] if d else 0,
            "discussion": d["url"] if d else "",
        }
    stats = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "extensions": out}
    path = os.path.join(ROOT, "stats.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        f.write("\n")
    print(f"stats: {len(out)} extensions")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
