import datetime
import time
from dataclasses import dataclass
from typing import Any

from feedparser import FeedParserDict
from reader import Entry


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    link: str
    abstract: str
    tags: list[dict[str, Any]]
    published: time.struct_time | datetime
    authors: str

    @classmethod
    def from_entry(cls, d: FeedParserDict | Entry) -> "Paper":
        if isinstance(d, FeedParserDict):
            return cls(
                id=d["id"],
                title=d["title"],
                link=d["link"],
                abstract=d["summary"],
                tags=d["tags"],
                published=d["published_parsed"],
                authors=d["authors"],
            )
        else:
            return cls(
                id=d.id,
                title=d.title,
                link=d.link,
                abstract=d.summary,
                tags=[],
                published=d.published,
                authors=d.author,
            )

    def to_serializable(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "abstract": self.abstract,
            "tags": self.tags,
            "published": str(self.published),
            "authors": self.authors,
        }


@dataclass(frozen=True)
class PaperAndSummary:
    paper: Paper
    summary: str

    def to_serializable(self) -> dict[str, Any]:
        return {
            "paper": self.paper.to_serializable(),
            "summary": self.summary,
        }

    def to_markdown(self) -> str:
        key_str = "Abstract: "
        abstract = self.paper.abstract
        abstract = abstract[abstract.find(key_str) + len(key_str) :]
        return f"""- [ ] [{self.paper.title}]({self.paper.link})
    - Summary: {self.summary}"""
