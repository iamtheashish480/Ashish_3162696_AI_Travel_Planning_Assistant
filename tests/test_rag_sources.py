from pathlib import Path

from rag_engine import DATA_SOURCES


def test_three_knowledge_sources_are_present():
    assert len(DATA_SOURCES) >= 3
    for source in DATA_SOURCES:
        assert Path(source["path"]).exists()
        assert source["title"]
        assert source["url"].startswith("https://")
