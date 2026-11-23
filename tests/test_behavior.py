from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from aibotlog.cli import main
from aibotlog.core import scan

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample.access.log"


def combined(
    day: str,
    path: str,
    ua: str = "-",
    referer: str = "-",
    host: str = "203.0.113.10",
) -> str:
    # day is YYYY-MM-DD; convert to combined log timestamp
    year, month, day_n = day.split("-")
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    mon = months[int(month) - 1]
    request = f"GET {path} HTTP/1.1"
    return (
        f'{host} - - [{day_n}/{mon}/{year}:12:00:00 +0000] '
        f'"{request}" 200 100 "{referer}" "{ua}"'
    )


def write_log(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_cli(argv: list[str], capsys) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_bot_counting(tmp_path: Path) -> None:
    log = write_log(
        tmp_path / "access.log",
        [
            combined("2026-11-01", "/a", ua="Mozilla/5.0 GPTBot/1.2"),
            combined("2026-11-01", "/b", ua="Mozilla/5.0 (compatible; GPTBot/1.1)"),
            combined("2026-11-01", "/c", ua="ChatGPT-User/1.0"),
            combined("2026-11-01", "/d", ua="ClaudeBot/1.0"),
            combined("2026-11-01", "/e", ua="Mozilla/5.0 (compatible; CCBot/2.0)"),
            combined(
                "2026-11-01",
                "/f",
                ua="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            ),
            combined(
                "2026-11-01",
                "/g",
                ua="Mozilla/5.0 (compatible; Googlebot/2.1; Google-Extended)",
            ),
            combined("2026-11-01", "/h", ua="Mozilla/5.0 Applebot/0.1"),
            combined("2026-11-01", "/i", ua="Mozilla/5.0 Applebot-Extended/0.1"),
            combined("2026-11-01", "/j", ua="meta-externalagent/1.1"),
            combined("2026-11-01", "/k", ua="Mozilla/5.0 (compatible; Amazonbot/0.1)"),
        ],
    )
    report = scan([str(log)])
    assert report.parsed == 11
    assert report.skipped == 0
    assert report.crawlers == {
        "GPTBot": 2,
        "ChatGPT-User": 1,
        "ClaudeBot": 1,
        "CCBot": 1,
        "Google-Extended": 1,
        "Applebot-Extended": 1,
        "meta-externalagent": 1,
        "Amazonbot": 1,
    }
    assert report.crawler_hits == 9
    assert "Googlebot" not in report.crawlers
    assert "Applebot" not in report.crawlers


def test_ai_referral_counting(tmp_path: Path) -> None:
    log = write_log(
        tmp_path / "access.log",
        [
            combined("2026-11-02", "/blog", referer="https://chatgpt.com/c/abc"),
            combined("2026-11-02", "/blog", referer="https://www.chatgpt.com/"),
            combined(
                "2026-11-02",
                "/docs",
                referer="https://chat.openai.com/chat",
            ),
            combined(
                "2026-11-02",
                "/pricing",
                referer="https://www.perplexity.ai/search?q=foo",
            ),
            combined("2026-11-02", "/docs", referer="https://claude.ai/chat/1"),
            combined(
                "2026-11-02",
                "/home",
                referer="https://news.example.com/item",
            ),
            combined("2026-11-02", "/home", referer="-"),
            combined(
                "2026-11-02",
                "/spoof",
                referer="https://chatgpt.com.attacker.example/x",
            ),
            combined("2026-11-02", "/gemini", referer="https://gemini.google.com/app"),
            combined("2026-11-02", "/grok", referer="https://grok.com/chat"),
        ],
    )
    report = scan([str(log)])
    assert report.parsed == 10
    assert report.referrals == {
        "chatgpt.com": 2,
        "chat.openai.com": 1,
        "perplexity.ai": 1,
        "claude.ai": 1,
        "gemini.google.com": 1,
        "grok.com": 1,
    }
    assert report.referral_hits == 7
    assert "example.com" not in report.referrals
    assert "attacker.example" not in report.referrals


def test_malformed_lines_skipped(tmp_path: Path) -> None:
    log = write_log(
        tmp_path / "access.log",
        [
            combined("2026-11-01", "/ok", ua="GPTBot/1.0"),
            "",
            "this is not a log line",
            "# comment",
            '203.0.113.9 - - [bad-date] "GET / HTTP/1.1" 200 1 "-" "GPTBot/1.0"',
            # common log format, missing referer and user-agent
            '203.0.113.8 - - [01/Nov/2026:12:00:00 +0000] "GET / HTTP/1.1" 200 1',
            combined("2026-11-01", "/also-ok", ua="ClaudeBot/1.0"),
        ],
    )
    report = scan([str(log)])
    assert report.lines == 7
    assert report.parsed == 2
    assert report.skipped == 5
    assert report.crawlers == {"GPTBot": 1, "ClaudeBot": 1}


def test_gz_input(tmp_path: Path) -> None:
    lines = [
        combined("2026-11-01", "/blog", ua="GPTBot/1.0"),
        combined("2026-11-01", "/docs", referer="https://chatgpt.com/"),
        "not parsed",
    ]
    plain = write_log(tmp_path / "access.log", lines)
    gz_path = tmp_path / "access.log.gz"
    with gzip.open(gz_path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    plain_report = scan([str(plain)])
    gz_report = scan([str(gz_path)])
    assert gz_report.parsed == plain_report.parsed == 2
    assert gz_report.skipped == plain_report.skipped == 1
    assert gz_report.crawlers == plain_report.crawlers == {"GPTBot": 1}
    assert gz_report.referrals == plain_report.referrals == {"chatgpt.com": 1}


def test_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(
        tmp_path / "access.log",
        [
            combined("2026-11-01", "/blog", ua="GPTBot/1.0"),
            combined("2026-11-02", "/docs", referer="https://chatgpt.com/c/1"),
            "garbage",
        ],
    )
    code, out, err = run_cli([str(log), "--json"], capsys)
    assert code == 0
    assert err == ""
    payload = json.loads(out)
    assert payload["parsed"] == 2
    assert payload["skipped"] == 1
    assert payload["crawlers"] == {"GPTBot": 1}
    assert payload["referrals"] == {"chatgpt.com": 1}
    assert payload["crawler_hits"] == 1
    assert payload["referral_hits"] == 1
    assert payload["by_day"] == [
        {"day": "2026-11-01", "crawlers": 1, "referrals": 0},
        {"day": "2026-11-02", "crawlers": 0, "referrals": 1},
    ]
    paths = {item["path"]: item for item in payload["by_path"]}
    assert paths["/blog"] == {"path": "/blog", "crawlers": 1, "referrals": 0}
    assert paths["/docs"] == {"path": "/docs", "crawlers": 0, "referrals": 1}


def test_day_and_path_breakdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(
        tmp_path / "access.log",
        [
            combined("2026-11-01", "/blog/ai-traffic?utm=1", ua="GPTBot/1.0"),
            combined("2026-11-01", "/robots.txt", ua="ClaudeBot/1.0"),
            combined("2026-11-02", "/blog/ai-traffic", ua="CCBot/2.0"),
            combined(
                "2026-11-02",
                "/blog/ai-traffic",
                referer="https://chatgpt.com/c/1",
            ),
            combined(
                "2026-11-02",
                "/pricing",
                referer="https://www.perplexity.ai/search?q=x",
            ),
        ],
    )
    report = scan([str(log)])
    assert report.day_crawlers == {"2026-11-01": 2, "2026-11-02": 1}
    assert report.day_referrals == {"2026-11-02": 2}
    assert report.path_crawlers == {"/blog/ai-traffic": 2, "/robots.txt": 1}
    assert report.path_referrals == {"/blog/ai-traffic": 1, "/pricing": 1}

    code, out, err = run_cli([str(log), "--by", "day"], capsys)
    assert code == 0
    assert err == ""
    assert "By day" in out
    assert "2026-11-01" in out
    assert "2026-11-02" in out
    assert "Top paths" not in out

    code, out, err = run_cli([str(log), "--by", "path", "--top", "1"], capsys)
    assert code == 0
    assert "Top paths" in out
    assert "/blog/ai-traffic" in out
    assert "/robots.txt" not in out
    assert "By day" not in out

    code, out, err = run_cli([str(log), "--json", "--by", "path", "--top", "1"], capsys)
    assert code == 0
    payload = json.loads(out)
    assert "by_day" not in payload
    assert payload["by_path"] == [
        {"path": "/blog/ai-traffic", "crawlers": 2, "referrals": 1}
    ]


def test_sample_log_and_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run_cli([str(SAMPLE)], capsys)
    assert code == 0
    assert "GPTBot" in out
    assert "chatgpt.com" in out
    assert "By day" in out
    assert "Top paths" in out

    missing = tmp_path / "nope.log"
    code, out, err = run_cli([str(missing)], capsys)
    assert code == 2
    assert "no such file" in err
    assert out == ""
