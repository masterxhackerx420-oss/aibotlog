# aibotlog

![aibotlog banner](docs/aibotlog-banner.jpg)

Count AI crawler hits and AI-answer referrals in nginx or apache access logs.

Requires Python 3.10+. No runtime dependencies. Reads the files you pass it, or stdin; it never fetches URLs or opens your browser.

```sh
pip install git+https://github.com/masterxhackerx420-oss/aibotlog
aibotlog access.log
aibotlog /var/log/nginx/access.log /var/log/nginx/access.log.1.gz
aibotlog access.log --by day
aibotlog access.log --by path --top 20
aibotlog access.log --json
gzip -dc access.log.gz | aibotlog
aibotlog --version
```

See [INSTALL.md](INSTALL.md) for isolated Windows/macOS/Linux installation.

## What it reports

Logs must be in the combined access log format used by nginx and apache: host, ident, user, timestamp, request, status, bytes, referer, and user-agent. Plain text and `.gz` files are accepted. Lines that do not parse are skipped and counted as skipped. The request path is taken without the query string.

**AI crawlers** are matched against the user-agent as whole tokens, case-insensitively: GPTBot, ChatGPT-User, OAI-SearchBot, ClaudeBot, Claude-User, Claude-SearchBot, anthropic-ai, PerplexityBot, Perplexity-User, Google-Extended, Google-CloudVertexBot, Applebot-Extended, Amazonbot, meta-externalagent, CCBot, Bytespider, Diffbot, YouBot, cohere-ai, and AI2Bot. Ordinary Googlebot or Applebot traffic is not counted unless the `-Extended` token is present. A line is assigned at most one bot name.

**AI referrals** are matched against the referer host, including subdomains: chatgpt.com, chat.openai.com, perplexity.ai, claude.ai, gemini.google.com, bard.google.com, copilot.microsoft.com, you.com, grok.com, and chat.mistral.ai. A line can count as both a crawler hit and a referral if both match.

Default output is a table of bots, a table of referral sources, a breakdown by day, and the top paths (default 10, change with `--top`). `--by day` or `--by path` keeps only that breakdown. `--json` prints the same counts as JSON. Exit status is 0 on a successful report, including when there are zero AI hits, and 2 if a file is missing or unreadable.

This is a log counter, not a bot blocker, a robots.txt auditor, or a claim about training-data use.

## Development

```sh
python -m pip install -e .
python -m pip install pytest
python -m pytest -q
```

Tests use fixture log snippets and do not need the network. MIT licensed.
