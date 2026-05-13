"""CLI entry point: serve / crawl / export."""

from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="topic-scout", description="TopicScout — personal research agent")
    sub = parser.add_subparsers(dest="command")

    # serve
    serve_p = sub.add_parser("serve", help="Start the API server")
    serve_p.add_argument("--host", default="0.0.0.0", help="Bind address")
    serve_p.add_argument("--port", type=int, default=8000, help="Port number")

    # crawl
    crawl_p = sub.add_parser("crawl", help="Crawl URLs directly")
    crawl_p.add_argument("urls", nargs="+", help="URLs to crawl")
    crawl_p.add_argument("--topic", default="cli", help="Topic ID for grouping")

    # export
    export_p = sub.add_parser("export", help="Export topic as JSON")
    export_p.add_argument("topic_id", help="Topic ID to export")

    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn
        from .config import config
        uvicorn.run(
            "topic_scout.server:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_level="info",
        )
    elif args.command == "crawl":
        from .crawler.web import WebCrawler
        async def run():
            crawler = WebCrawler()
            for url in args.urls:
                result = await crawler.crawl_with_retry(url, topic_id=args.topic, version=1)
                if result:
                    print(f"[OK] {result.title}: {len(result.content)} chars")
                else:
                    print(f"[FAIL] {url}")
        asyncio.run(run())
    elif args.command == "export":
        from . import db
        from .exporter import export_json
        async def run():
            topic = await db.get_topic(args.topic_id)
            if not topic:
                print(f"Topic {args.topic_id} not found")
                sys.exit(1)
            sources = await db.get_sources(args.topic_id)
            summary = await db.get_summary(args.topic_id)
            path = export_json(topic, sources, summary)
            print(f"Exported to {path}")
        asyncio.run(run())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
