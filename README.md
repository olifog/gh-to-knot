# github-tangled-mirror

bidirectional mirror between github and a [tangled](https://tangled.org) knot server.

queries your knot's database for registered repos, checks which ones exist on github, and syncs them. source of truth is determined by `SYNC_DIRECTION`.

## setup

```bash
cp .env.example .env  # edit with your values
docker compose up -d
```

syncs every 2 minutes by default. set `SYNC_INTERVAL` (seconds) to change.

set `GITHUB_TOKEN` for private repos or if you have >60 repos.

set `SYNC_DIRECTION` to `github-to-knot` (default) or `knot-to-github`.

repos must already exist on both sides (create on tangled via the web UI with the same name as your github repo).

## todo

- [ ] auto-create repos on tangled
- [ ] webhook trigger instead of polling
- [ ] parallel sync
