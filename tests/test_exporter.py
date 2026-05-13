"""Tests for the exporter."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from topic_scout.exporter import export_json
from topic_scout.models import Platform, Source, Summary, Topic


@pytest.fixture
def tmp_export_dir():
    d = tempfile.mkdtemp()
    yield d


class TestExportJson:
    def test_export_creates_file(self, tmp_export_dir: str):
        import topic_scout.config as cfg
        old_dir = cfg.config.storage.exports_dir
        cfg.config.storage.exports_dir = tmp_export_dir

        try:
            topic = Topic(id="test_001", keyword="AI", title="AI Research", description="About AI")
            sources = [
                Source(
                    id="src_1",
                    topic_id="test_001",
                    platform=Platform.WEB,
                    url="https://example.com",
                    title="Example",
                    content="Content here",
                    summary="Summary here",
                    category="技术",
                    confidence=0.9,
                ),
            ]
            summary = Summary(
                topic_id="test_001",
                content="Global summary",
                key_insights=["Insight 1", "Insight 2"],
            )

            path = export_json(topic, sources, summary)
            assert os.path.exists(path)

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            assert data["meta"]["topic_id"] == "test_001"
            assert data["meta"]["keyword"] == "AI"
            assert data["meta"]["total_sources"] == 1
            assert data["summary"]["content"] == "Global summary"
            assert len(data["summary"]["key_insights"]) == 2
            assert len(data["sources"]) == 1
            assert data["sources"][0]["id"] == "src_1"
            assert data["sources"][0]["platform"] == "web"
            assert len(data["categories"]) == 1
            assert data["categories"][0]["name"] == "技术"
        finally:
            cfg.config.storage.exports_dir = old_dir

    def test_export_without_summary(self, tmp_export_dir: str):
        import topic_scout.config as cfg
        old_dir = cfg.config.storage.exports_dir
        cfg.config.storage.exports_dir = tmp_export_dir

        try:
            topic = Topic(id="test_002", keyword="test")
            sources = [
                Source(id="src_a", topic_id="test_002", platform=Platform.WEB, title="A", category="Cat1"),
                Source(id="src_b", topic_id="test_002", platform=Platform.WEB, title="B", category="Cat1"),
                Source(id="src_c", topic_id="test_002", platform=Platform.WEB, title="C", category="Cat2"),
            ]

            path = export_json(topic, sources, None)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            assert data["summary"] is None
            assert len(data["categories"]) == 2
            cats = {c["name"]: c["sources"] for c in data["categories"]}
            assert len(cats["Cat1"]) == 2
            assert len(cats["Cat2"]) == 1
        finally:
            cfg.config.storage.exports_dir = old_dir
