#!/usr/bin/env python3
"""
FOLIO API Traffic Analytics

Usage:
    uv run --with rich,polars python analytics.py [options]

If logs are only readable by root:
    sudo "$(which uv)" run --with rich,polars python analytics.py [options]

Options:
    --days N      Only analyze last N days (default: all)
    --live        Only analyze current access.log (default)
    --current     Alias for --live
    --all         Include gzipped rotated logs too
    --top N       How many entries in "top" tables (default: 15)
"""

import argparse
import gzip
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ── Log directory discovery ──────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs" / "caddy"

# ── Bot classification ───────────────────────────────────────────────────

BOT_PATTERNS = [
    ("AhrefsBot", "AhrefsBot"),
    ("Amazonbot", "Amazonbot"),
    ("Barkrowler", "Barkrowler"),
    ("Bytespider", "Bytespider"),
    ("ClaudeBot", "ClaudeBot"),
    ("DotBot", "DotBot"),
    ("Googlebot", "Googlebot"),
    ("GPTBot", "GPTBot"),
    ("MJ12bot", "MJ12bot"),
    ("PetalBot", "PetalBot"),
    ("SemrushBot", "SemrushBot"),
    ("YandexBot", "YandexBot"),
    ("bingbot", "Bingbot"),
    ("meta-externalagent", "Meta/Facebook"),
    ("facebookexternalhit", "Meta/Facebook"),
    ("Python-urllib", "Python-urllib"),
    ("python-requests", "python-requests"),
    ("Go-http-client", "Go-http-client"),
    ("curl/", "curl"),
    ("wget", "wget"),
    ("Applebot", "Applebot"),
    ("DataForSeoBot", "DataForSeoBot"),
    ("BLEXBot", "BLEXBot"),
    ("ZoominfoBot", "ZoominfoBot"),
    ("CCBot", "CCBot"),
    ("LinkedInBot", "LinkedInBot"),
    ("Twitterbot", "Twitterbot"),
    ("ia_archiver", "InternetArchive"),
    ("spider", "spider (generic)"),
    ("crawler", "crawler (generic)"),
    ("bot/", "bot (generic)"),
    ("Bot/", "bot (generic)"),
]

# ── Endpoint classification ──────────────────────────────────────────────

def classify_endpoint(uri: str) -> str:
    """Classify a URI into a logical endpoint category."""
    if uri.startswith("/search/llm"):
        return "Search (LLM)"
    if uri.startswith("/search/"):
        return "Search (text)"
    if uri.startswith("/taxonomy/"):
        return "Taxonomy"
    if uri.startswith("/properties/"):
        return "Properties"
    if uri.startswith("/explore/"):
        return "Explore"
    if uri == "/docs" or uri.startswith("/docs/") or uri == "/openapi.json":
        return "Docs/OpenAPI"
    if uri.startswith("/static/"):
        return "Static assets"
    if uri == "/health" or uri == "/healthz" or uri == "/ready":
        return "Health"
    if uri == "/robots.txt" or uri == "/favicon.ico" or uri == "/sitemap.xml":
        return "Robots/meta"
    if uri == "/api" or uri.startswith("/api/"):
        return "API root"
    if uri == "/":
        return "Homepage"
    # Class lookups: /R<id> or /R<id>/format or short-id patterns
    if re.match(r"^/[A-Za-z0-9_-]{10,}", uri):
        parts = uri.split("/")
        if len(parts) >= 3 and parts[2] in ("html", "xml", "jsonld", "markdown", "json", "turtle", "ntriples"):
            return f"Class lookup ({parts[2]})"
        return "Class lookup (default)"
    return "Other"


def classify_bot(ua: str) -> str:
    """Return bot name if user-agent matches a known bot, else 'Human'."""
    if not ua:
        return "Bot (empty UA)"
    for pattern, name in BOT_PATTERNS:
        if pattern in ua:
            return name
    return "Human"


# ── Log parsing ──────────────────────────────────────────────────────────

def parse_log_lines(lines):
    """Parse JSON log lines into a list of row dicts."""
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        req = entry.get("request", {})
        headers = req.get("headers", {})
        ua_list = headers.get("User-Agent", [""])
        ua = ua_list[0] if ua_list else ""

        uri = req.get("uri", "")
        ts = entry.get("ts", 0)

        rows.append({
            "ts": ts,
            "method": req.get("method", ""),
            "uri": uri,
            "status": entry.get("status", 0),
            "size": entry.get("size", 0),
            "duration": entry.get("duration", 0.0),
            "remote_ip": req.get("client_ip", req.get("remote_ip", "")),
            "user_agent": ua,
            "host": req.get("host", ""),
        })
    return rows


def load_logs(include_archives: bool) -> pl.DataFrame:
    """Load log data into a polars DataFrame."""
    all_rows = []

    access_log = LOG_DIR / "access.log"
    if access_log.exists():
        console.print(f"  Reading [cyan]{access_log.name}[/]…")
        try:
            with open(access_log, "r") as f:
                all_rows.extend(parse_log_lines(f))
        except PermissionError:
            console.print(f"  [yellow]Permission denied: {access_log}. Try running with sudo.[/]")

    if include_archives:
        gz_files = sorted(LOG_DIR.glob("access-*.log.gz"))
        for gz_file in gz_files:
            console.print(f"  Reading [cyan]{gz_file.name}[/]…")
            try:
                with gzip.open(gz_file, "rt") as f:
                    all_rows.extend(parse_log_lines(f))
            except PermissionError:
                console.print(f"  [yellow]Permission denied: {gz_file}. Try running with sudo.[/]")

    if not all_rows:
        console.print("[red]No log data found![/]")
        sys.exit(1)

    df = pl.DataFrame(all_rows)

    # Add derived columns
    df = df.with_columns([
        pl.from_epoch(pl.col("ts"), time_unit="s").alias("datetime"),
        pl.col("uri").map_elements(classify_endpoint, return_dtype=pl.Utf8).alias("category"),
        pl.col("user_agent").map_elements(classify_bot, return_dtype=pl.Utf8).alias("bot_class"),
    ])

    return df


# ── Output sections ──────────────────────────────────────────────────────

def show_overview(df: pl.DataFrame):
    dt_col = df["datetime"]
    date_min = dt_col.min()
    date_max = dt_col.max()
    total = len(df)
    unique_ips = df["remote_ip"].n_unique()
    total_bytes = df["size"].sum()
    avg_latency = df["duration"].mean()
    median_latency = df["duration"].median()

    def fmt_bytes(b):
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(b) < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"

    lines = [
        f"[bold]Total requests:[/]   {total:,}",
        f"[bold]Date range:[/]       {date_min.strftime('%Y-%m-%d %H:%M')} → {date_max.strftime('%Y-%m-%d %H:%M')}",
        f"[bold]Unique IPs:[/]       {unique_ips:,}",
        f"[bold]Total bandwidth:[/]  {fmt_bytes(total_bytes)}",
        f"[bold]Avg latency:[/]      {avg_latency * 1000:.1f} ms",
        f"[bold]Median latency:[/]   {median_latency * 1000:.1f} ms",
    ]
    console.print(Panel("\n".join(lines), title="Overview", border_style="blue"))


def show_daily_chart(df: pl.DataFrame):
    daily = (
        df.with_columns(pl.col("datetime").dt.date().alias("date"))
        .group_by("date")
        .agg(pl.len().alias("count"))
        .sort("date")
        .tail(14)
    )

    if daily.is_empty():
        return

    dates = daily["date"].to_list()
    counts = daily["count"].to_list()
    max_count = max(counts)
    bar_width = 40

    lines = []
    for date, count in zip(dates, counts):
        bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {date}  {bar} {count:,}")

    console.print(Panel("\n".join(lines), title="Requests by Day (last 14 days)", border_style="green"))


def show_endpoint_categories(df: pl.DataFrame):
    cats = (
        df.group_by("category")
        .agg([
            pl.len().alias("count"),
            pl.col("duration").mean().alias("avg_ms"),
        ])
        .sort("count", descending=True)
    )

    table = Table(title="Endpoint Categories", show_lines=False)
    table.add_column("Category", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("%", justify="right")
    table.add_column("Avg Latency", justify="right")

    total = len(df)
    for row in cats.iter_rows(named=True):
        pct = (row["count"] / total * 100) if total > 0 else 0
        table.add_row(
            row["category"],
            f"{row['count']:,}",
            f"{pct:.1f}%",
            f"{row['avg_ms'] * 1000:.1f} ms",
        )
    console.print(table)


def show_status_codes(df: pl.DataFrame):
    status = (
        df.group_by("status")
        .agg(pl.len().alias("count"))
        .sort("status")
    )

    # Also compute grouped (2xx, 3xx, etc.)
    grouped = (
        df.with_columns((pl.col("status") // 100).alias("status_group"))
        .group_by("status_group")
        .agg(pl.len().alias("count"))
        .sort("status_group")
    )

    table = Table(title="Status Code Distribution", show_lines=False)
    table.add_column("Group", style="bold")
    table.add_column("Requests", justify="right")
    table.add_column("%", justify="right")

    total = len(df)
    group_colors = {2: "green", 3: "yellow", 4: "red", 5: "bold red"}
    for row in grouped.iter_rows(named=True):
        g = row["status_group"]
        pct = (row["count"] / total * 100) if total > 0 else 0
        color = group_colors.get(g, "white")
        table.add_row(f"[{color}]{g}xx[/]", f"{row['count']:,}", f"{pct:.1f}%")

    # Detail rows
    table.add_section()
    for row in status.iter_rows(named=True):
        pct = (row["count"] / total * 100) if total > 0 else 0
        s = row["status"]
        color = group_colors.get(s // 100, "white")
        table.add_row(f"  [{color}]{s}[/]", f"{row['count']:,}", f"{pct:.1f}%")

    console.print(table)


def show_top_paths(df: pl.DataFrame, top_n: int):
    paths = (
        df.group_by("uri")
        .agg([
            pl.len().alias("count"),
            pl.col("status").mode().first().alias("common_status"),
        ])
        .sort("count", descending=True)
        .head(top_n)
    )

    table = Table(title=f"Top {top_n} Paths", show_lines=False)
    table.add_column("Path", style="cyan", max_width=70)
    table.add_column("Requests", justify="right")
    table.add_column("Status", justify="right")

    for row in paths.iter_rows(named=True):
        uri = row["uri"]
        if len(uri) > 70:
            uri = uri[:67] + "…"
        table.add_row(uri, f"{row['count']:,}", str(row["common_status"]))
    console.print(table)


def show_bot_vs_human(df: pl.DataFrame, top_n: int):
    is_bot = df["bot_class"] != "Human"
    bot_count = is_bot.sum()
    human_count = len(df) - bot_count
    total = len(df)

    lines = [
        f"  [green]Human:[/]  {human_count:>8,}  ({human_count / total * 100:.1f}%)",
        f"  [red]Bot:[/]    {bot_count:>8,}  ({bot_count / total * 100:.1f}%)",
    ]
    console.print(Panel("\n".join(lines), title="Bot vs Human Traffic", border_style="magenta"))

    # Bot breakdown
    bots = (
        df.filter(pl.col("bot_class") != "Human")
        .group_by("bot_class")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .head(top_n)
    )

    if bots.is_empty():
        return

    table = Table(title="Top Bots", show_lines=False)
    table.add_column("Bot", style="red")
    table.add_column("Requests", justify="right")
    table.add_column("% of Total", justify="right")

    for row in bots.iter_rows(named=True):
        pct = (row["count"] / total * 100) if total > 0 else 0
        table.add_row(row["bot_class"], f"{row['count']:,}", f"{pct:.1f}%")
    console.print(table)


def show_top_ips(df: pl.DataFrame, top_n: int):
    ips = (
        df.group_by("remote_ip")
        .agg([
            pl.len().alias("count"),
            pl.col("bot_class").mode().first().alias("likely_class"),
        ])
        .sort("count", descending=True)
        .head(top_n)
    )

    table = Table(title=f"Top {top_n} IPs", show_lines=False)
    table.add_column("IP Address", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("Classification")

    for row in ips.iter_rows(named=True):
        cls = row["likely_class"]
        style = "green" if cls == "Human" else "red"
        table.add_row(row["remote_ip"], f"{row['count']:,}", f"[{style}]{cls}[/]")
    console.print(table)


def show_llm_search(df: pl.DataFrame):
    llm = df.filter(pl.col("uri").str.starts_with("/search/llm"))
    if llm.is_empty():
        console.print(Panel("[dim]No LLM search requests found in this data.[/]", title="LLM Search Usage", border_style="yellow"))
        return

    by_path = (
        llm.group_by("uri")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .head(15)
    )

    table = Table(title="LLM Search Usage", show_lines=False)
    table.add_column("Endpoint", style="yellow")
    table.add_column("Requests", justify="right")

    for row in by_path.iter_rows(named=True):
        table.add_row(row["uri"], f"{row['count']:,}")

    total_llm = len(llm)
    avg_dur = llm["duration"].mean() * 1000
    console.print(table)
    console.print(f"  Total LLM search requests: [bold]{total_llm:,}[/]  |  Avg latency: [bold]{avg_dur:.0f} ms[/]")


def show_latency_stats(df: pl.DataFrame, top_n: int):
    dur = df["duration"]
    p50 = dur.quantile(0.5) * 1000
    p90 = dur.quantile(0.9) * 1000
    p95 = dur.quantile(0.95) * 1000
    p99 = dur.quantile(0.99) * 1000
    p999 = dur.quantile(0.999) * 1000
    max_dur = dur.max() * 1000

    lines = [
        f"  p50:   {p50:>8.1f} ms",
        f"  p90:   {p90:>8.1f} ms",
        f"  p95:   {p95:>8.1f} ms",
        f"  p99:   {p99:>8.1f} ms",
        f"  p99.9: {p999:>8.1f} ms",
        f"  max:   {max_dur:>8.1f} ms",
    ]
    console.print(Panel("\n".join(lines), title="Latency Percentiles", border_style="cyan"))

    # Slowest endpoint categories
    slow = (
        df.group_by("category")
        .agg([
            pl.col("duration").mean().alias("avg_ms"),
            pl.col("duration").quantile(0.95).alias("p95_ms"),
            pl.len().alias("count"),
        ])
        .filter(pl.col("count") >= 10)
        .sort("p95_ms", descending=True)
        .head(top_n)
    )

    table = Table(title="Slowest Endpoint Categories (p95, min 10 requests)", show_lines=False)
    table.add_column("Category", style="cyan")
    table.add_column("Avg", justify="right")
    table.add_column("p95", justify="right")
    table.add_column("Requests", justify="right")

    for row in slow.iter_rows(named=True):
        table.add_row(
            row["category"],
            f"{row['avg_ms'] * 1000:.1f} ms",
            f"{row['p95_ms'] * 1000:.1f} ms",
            f"{row['count']:,}",
        )
    console.print(table)


def show_hourly_heatmap(df: pl.DataFrame):
    hourly = (
        df.with_columns(pl.col("datetime").dt.hour().alias("hour"))
        .group_by("hour")
        .agg(pl.len().alias("count"))
        .sort("hour")
    )

    # Fill in missing hours
    hour_counts = {row["hour"]: row["count"] for row in hourly.iter_rows(named=True)}
    counts = [hour_counts.get(h, 0) for h in range(24)]
    max_count = max(counts) if counts else 1
    bar_width = 30

    lines = []
    for h in range(24):
        c = counts[h]
        bar_len = int((c / max_count) * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {h:02d}:00  {bar} {c:,}")

    console.print(Panel("\n".join(lines), title="Requests by Hour (UTC)", border_style="blue"))


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FOLIO API Traffic Analytics")
    parser.add_argument("--days", type=int, default=0, help="Only analyze last N days (default: all)")
    parser.add_argument("--live", "--current", action="store_true", default=True, help="Only current access.log (default)")
    parser.add_argument("--all", action="store_true", dest="include_all", help="Include gzipped rotated logs")
    parser.add_argument("--top", type=int, default=15, help="Entries in 'top' tables (default: 15)")
    args = parser.parse_args()

    if not LOG_DIR.exists():
        console.print(f"[red]Log directory not found: {LOG_DIR}[/]")
        sys.exit(1)

    console.print(Panel("[bold]FOLIO API Traffic Analytics[/]", border_style="bright_blue"))
    console.print(f"Log directory: [dim]{LOG_DIR}[/]")

    include_archives = args.include_all
    if include_archives:
        console.print("Mode: [bold]all logs[/] (current + archives)")
    else:
        console.print("Mode: [bold]current log only[/] (use --all for archives)")

    console.print()
    df = load_logs(include_archives)
    console.print(f"Loaded [bold]{len(df):,}[/] log entries.\n")

    # Filter by --days
    if args.days > 0:
        cutoff = df["datetime"].max() - pl.duration(days=args.days)
        df = df.filter(pl.col("datetime") >= cutoff)
        console.print(f"Filtered to last {args.days} day(s): [bold]{len(df):,}[/] entries.\n")

    if df.is_empty():
        console.print("[red]No data to analyze after filtering.[/]")
        sys.exit(1)

    top_n = args.top

    show_overview(df)
    console.print()
    show_daily_chart(df)
    console.print()
    show_endpoint_categories(df)
    console.print()
    show_status_codes(df)
    console.print()
    show_top_paths(df, top_n)
    console.print()
    show_bot_vs_human(df, top_n)
    console.print()
    show_top_ips(df, top_n)
    console.print()
    show_llm_search(df)
    console.print()
    show_latency_stats(df, top_n)
    console.print()
    show_hourly_heatmap(df)


if __name__ == "__main__":
    main()
