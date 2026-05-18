#!/usr/bin/env python3
"""Mirror repos between GitHub and a Tangled knot server."""

import os
import sqlite3
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

GITHUB_USER = os.environ.get("GITHUB_USER", "olifog")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
MIRROR_DIR = Path(os.environ.get("MIRROR_DIR", "/mirrors"))
CONTAINER = os.environ.get("KNOT_CONTAINER", "knot-knot-1")
REPO_BASE = os.environ.get("KNOT_REPO_BASE", "/home/git/repositories")
DB_PATH = os.environ.get("KNOT_DB_PATH", "/data/knotserver.db")
DIRECTION = os.environ.get("SYNC_DIRECTION", "github-to-knot")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def github_request(url: str, method: str = "GET") -> urllib.request.Request:
    req = urllib.request.Request(url, method=method)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    return req


def github_repo_exists(user: str, name: str) -> bool:
    req = github_request(f"https://api.github.com/repos/{user}/{name}", method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError:
        return False


def github_clone_url(name: str) -> str:
    if GITHUB_TOKEN:
        return f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{name}.git"
    return f"https://github.com/{GITHUB_USER}/{name}.git"


def get_knot_repos(db_path: str) -> list[tuple[str, str]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT rkey, repo_did FROM repo_aliases")
    repos = cur.fetchall()
    conn.close()
    return repos


def sync_github_to_knot(name: str, repo_did: str) -> None:
    url = github_clone_url(name)
    repo_dir = MIRROR_DIR / f"{name}.git"

    if repo_dir.exists():
        print(f"[fetch] {name} <- github")
        run(["git", "-C", str(repo_dir), "remote", "set-url", "origin", url])
        run(["git", "-C", str(repo_dir), "fetch", "--prune", "origin"])
    else:
        print(f"[clone] {name} <- github")
        run(["git", "clone", "--mirror", url, str(repo_dir)])

    print(f"[push] {name} -> knot")
    container_path = f"/tmp/mirror-{name}.git"
    dst = f"{REPO_BASE}/{repo_did}"

    run(["docker", "cp", str(repo_dir), f"{CONTAINER}:{container_path}"])
    run(["docker", "exec", "-u", "git", CONTAINER,
         "git", "config", "--global", "--add", "safe.directory", container_path])
    result = run(["docker", "exec", "-u", "git", "-w", container_path, CONTAINER,
                  "git", "push", "--mirror", dst])
    if result.returncode != 0 and result.stderr:
        print(f"  {result.stderr.strip()}")
    run(["docker", "exec", CONTAINER, "rm", "-rf", container_path])


def sync_knot_to_github(name: str, repo_did: str) -> None:
    repo_dir = MIRROR_DIR / f"{name}.git"
    container_path = f"/tmp/mirror-{name}.git"
    src = f"{REPO_BASE}/{repo_did}"

    print(f"[fetch] {name} <- knot")
    run(["docker", "exec", "-u", "git", CONTAINER,
         "git", "config", "--global", "--add", "safe.directory", src])
    run(["docker", "exec", CONTAINER, "rm", "-rf", container_path])
    result = run(["docker", "exec", "-u", "git", CONTAINER,
                  "git", "clone", "--mirror", src, container_path])
    if result.returncode != 0:
        print(f"  {result.stderr.strip()}")
        return

    run(["docker", "cp", f"{CONTAINER}:{container_path}", str(repo_dir)])
    run(["docker", "exec", CONTAINER, "rm", "-rf", container_path])

    url = github_clone_url(name)
    print(f"[push] {name} -> github")
    run(["git", "-C", str(repo_dir), "remote", "set-url", "origin", url])
    result = run(["git", "-C", str(repo_dir), "push", "--mirror", "origin"])
    if result.returncode != 0 and result.stderr:
        print(f"  {result.stderr.strip()}")


def main():
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)

    if GITHUB_TOKEN:
        print(f"[auth] using token (5000 req/hr)")
    else:
        print(f"[auth] unauthenticated (60 req/hr)")

    print(f"[mode] {DIRECTION}")

    repos = get_knot_repos(DB_PATH)
    if not repos:
        print("[warn] no repos found in knot DB")
        return

    for name, repo_did in repos:
        if not github_repo_exists(GITHUB_USER, name):
            print(f"[skip] {name} (not on GitHub)")
            continue

        if DIRECTION == "github-to-knot":
            sync_github_to_knot(name, repo_did)
        elif DIRECTION == "knot-to-github":
            sync_knot_to_github(name, repo_did)
        else:
            print(f"[error] unknown SYNC_DIRECTION: {DIRECTION}")
            return

    print(f"[done] {datetime.now():%Y-%m-%d %H:%M:%S}")


if __name__ == "__main__":
    main()
