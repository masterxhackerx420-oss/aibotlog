"""Parse combined access logs and count AI crawler hits and AI referrals."""

from __future__ import annotations

import gzip
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

# More specific names come first so ChatGPT-User is not classified as GPTBot
# if both tokens ever appear, and Applebot-Extended is distinct from Applebot.
AI_BOTS = (
    "OAI-SearchBot",
    "ChatGPT-User",
    "GPTBot",
    "Claude-SearchBot",
    "Claude-User",
    "ClaudeBot",
    "anthropic-ai",
    "Perplexity-User",
    "PerplexityBot",
    "Google-CloudVertexBot",
    "Google-Extended",
    "Applebot-Extended",
    "meta-externalagent",
    "Amazonbot",
    "Bytespider",
    "CCBot",
    "Diffbot",
    "YouBot",
    "cohere-ai",
    "AI2Bot",
)

AI_REFERRERS = (
    "chatgpt.com",
    "chat.openai.com",
    "perplexity.ai",
    "claude.ai",
    "gemini.google.com",
    "bard.google.com",
    "copilot.microsoft.com",
    "you.com",
    "grok.com",
    "chat.mistral.ai",
)

# host ident authuser [date] "request" status bytes "referer" "user-agent"
COMBINED = re.compile(
    r"^\S+ \S+ \S+ \[([^\]]+)\] \"([^\"]*)\" \S+ \S+ \"([^\"]*)\" \"([^\"]*)\""
)

_BOT_PATTERNS = tuple(
    (
        name,
        re.compile(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", re.I),
    )
    for name in AI_BOTS
)


@dataclass
class Report:
    files: list[str] = field(default_factory=list)
    lines: int = 0
    parsed: int = 0
    skipped: int = 0
    crawlers: Counter[str] = field(default_factory=Counter)
    referrals: Counter[str] = field(default_factory=Counter)
    day_crawlers: Counter[str] = field(default_factory=Counter)
    day_referrals: Counter[str] = field(default_factory=Counter)
    path_crawlers: Counter[str] = field(default_factory=Counter)
    path_referrals: Counter[str] = field(default_factory=Counter)

    @property
    def crawler_hits(self) -> int:
        return int(sum(self.crawlers.values()))

    @property
    def referral_hits(self) -> int:
        return int(sum(self.referrals.values()))


def parse_day(timestamp: str) -> str | None:
    stamp = timestamp.split()[0] if timestamp else ""
    try:
        return datetime.strptime(stamp, "%d/%b/%Y:%H:%M:%S").strftime("%Y-%m-%d")
    except ValueError:
        return None


def request_path(request: str) -> str:
    parts = request.split()
    if len(parts) >= 2:
        raw = parts[1]
    elif parts:
        raw = parts[0]
    else:
        return "-"
    if raw == "-":
        return "-"
    return urlparse(raw).path or "/"


def referrer_host(referer: str) -> str | None:
    if not referer or referer == "-":
        return None
    host = urlparse(referer).hostname
    if not host:
        return None
    return host.lower().rstrip(".")


def match_bot(user_agent: str) -> str | None:
    if not user_agent or user_agent == "-":
        return None
    for name, pattern in _BOT_PATTERNS:
        if pattern.search(user_agent):
            return name
    return None


def match_referrer(host: str | None) -> str | None:
    if not host:
        return None
    for domain in AI_REFERRERS:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


def parse_line(line: str) -> tuple[str, str, str | None, str | None] | None:
    """Return (day, path, bot, referrer source) or None if the line is unusable."""
    line = line.rstrip("\n\r")
    if not line or line.startswith("#"):
        return None
    match = COMBINED.match(line)
    if not match:
        return None
    day = parse_day(match.group(1))
    if day is None:
        return None
    path = request_path(match.group(2))
    bot = match_bot(match.group(4))
    source = match_referrer(referrer_host(match.group(3)))
    return day, path, bot, source


def iter_log_lines(path: str):
    if path == "-":
        yield from sys.stdin
        return
    opener = gzip.open if path.lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        yield from handle


def scan(paths: list[str]) -> Report:
    if not paths:
        paths = ["-"]
    report = Report(files=list(paths))
    for file_path in paths:
        for line in iter_log_lines(file_path):
            report.lines += 1
            parsed = parse_line(line)
            if parsed is None:
                report.skipped += 1
                continue
            report.parsed += 1
            day, url_path, bot, source = parsed
            if bot:
                report.crawlers[bot] += 1
                report.day_crawlers[day] += 1
                report.path_crawlers[url_path] += 1
            if source:
                report.referrals[source] += 1
                report.day_referrals[day] += 1
                report.path_referrals[url_path] += 1
    return report


def _ranked_paths(report: Report, top: int) -> list[dict[str, object]]:
    names = set(report.path_crawlers) | set(report.path_referrals)
    ranked = sorted(
        names,
        key=lambda name: (
            -(report.path_crawlers[name] + report.path_referrals[name]),
            name,
        ),
    )
    return [
        {
            "path": name,
            "crawlers": report.path_crawlers[name],
            "referrals": report.path_referrals[name],
        }
        for name in ranked[:top]
    ]


def report_to_dict(
    report: Report, *, by: str | None = None, top: int = 10
) -> dict[str, object]:
    days = sorted(set(report.day_crawlers) | set(report.day_referrals))
    payload: dict[str, object] = {
        "files": report.files,
        "lines": report.lines,
        "parsed": report.parsed,
        "skipped": report.skipped,
        "crawler_hits": report.crawler_hits,
        "referral_hits": report.referral_hits,
        "crawlers": dict(report.crawlers.most_common()),
        "referrals": dict(report.referrals.most_common()),
    }
    if by in (None, "day"):
        payload["by_day"] = [
            {
                "day": day,
                "crawlers": report.day_crawlers[day],
                "referrals": report.day_referrals[day],
            }
            for day in days
        ]
    if by in (None, "path"):
        payload["by_path"] = _ranked_paths(report, top)
    return payload


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]], right: set[int]) -> list[str]:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def fmt(row: tuple[str, ...]) -> str:
        parts = []
        for index, cell in enumerate(row):
            parts.append(cell.rjust(widths[index]) if index in right else cell.ljust(widths[index]))
        return "  ".join(parts)

    lines = [fmt(headers), "  ".join("-" * width for width in widths)]
    lines.extend(fmt(row) for row in rows)
    return lines


def render_report(report: Report, *, by: str | None = None, top: int = 10) -> str:
    lines = [
        (
            f"parsed {report.parsed} lines, skipped {report.skipped} "
            f"({report.crawler_hits} crawler hits, {report.referral_hits} AI referrals)"
        ),
        "",
        "AI crawlers",
    ]
    if report.crawlers:
        lines.extend(
            _table(
                ("bot", "hits"),
                tuple((name, str(count)) for name, count in report.crawlers.most_common()),
                {1},
            )
        )
    else:
        lines.append("(none)")

    lines.extend(["", "AI referrals"])
    if report.referrals:
        lines.extend(
            _table(
                ("source", "hits"),
                tuple((name, str(count)) for name, count in report.referrals.most_common()),
                {1},
            )
        )
    else:
        lines.append("(none)")

    if by in (None, "day"):
        days = sorted(set(report.day_crawlers) | set(report.day_referrals))
        lines.extend(["", "By day"])
        if days:
            lines.extend(
                _table(
                    ("day", "crawlers", "referrals"),
                    tuple(
                        (
                            day,
                            str(report.day_crawlers[day]),
                            str(report.day_referrals[day]),
                        )
                        for day in days
                    ),
                    {1, 2},
                )
            )
        else:
            lines.append("(none)")

    if by in (None, "path"):
        paths = _ranked_paths(report, top)
        lines.extend(["", "Top paths"])
        if paths:
            lines.extend(
                _table(
                    ("path", "crawlers", "referrals"),
                    tuple(
                        (
                            str(item["path"]),
                            str(item["crawlers"]),
                            str(item["referrals"]),
                        )
                        for item in paths
                    ),
                    {1, 2},
                )
            )
        else:
            lines.append("(none)")

    return "\n".join(lines) + "\n"


def dumps_report(report: Report, *, by: str | None = None, top: int = 10) -> str:
    return json.dumps(report_to_dict(report, by=by, top=top), indent=2) + "\n"
