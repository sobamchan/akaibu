from dataclasses import dataclass
from pathlib import Path

from reader import Reader, make_reader

from akaibu.checker import Checker
from akaibu.paper import Paper, PaperAndSummary
from akaibu.summarizer import PaperSummarizer


@dataclass(frozen=True)
class Library:
    reader: Reader

    @classmethod
    def load_default(cls) -> "Library":
        reader = make_reader("debug.sqlite")
        return cls(reader)

    @classmethod
    def load_from_path(cls, path: Path, remake: bool = False) -> "Library":
        if remake and path.exists():
            path.unlink()
        reader = make_reader(str(path))
        return cls(reader)

    def add_url(self, url: str) -> None:
        self.reader.add_feed(url, exist_ok=True)
        self.reader.update_feeds()

    def list_urls(self) -> list[str]:
        return [feed.link for feed in self.reader.get_feeds()]

    def get_papers(
        self,
        limit: int = 25,
        checker: Checker | None = None,
        summarizer: PaperSummarizer | None = None,
    ) -> list[Paper] | list[PaperAndSummary]:
        self.reader.update_feeds()
        entries = self.reader.get_entries(limit=limit, read=False)
        papers = []
        for entry in entries:
            self.reader.mark_entry_as_read(entry)
            paper = Paper.from_entry(entry)

            if checker and summarizer:
                is_relevant = checker.is_paper_relevant(paper)
                if is_relevant:
                    paper_and_summary = summarizer.summarize(paper)
                    self.reader.set_tag(entry, "is_relevant", True)
                    self.reader.set_tag(
                        entry, "generated_summary", paper_and_summary.summary
                    )
                    papers.append(paper_and_summary)
            else:
                papers.append(Paper.from_entry(entry))
        return papers

    def get_past_relevant_papers(self) -> list[PaperAndSummary]:
        entries = self.reader.get_entries(read=True, tags=["is_relevant"])
        papers = []
        for ent in entries:
            generated_summary: str = dict(self.reader.get_tags(ent))[
                "generated_summary"
            ]
            paper = PaperAndSummary(Paper.from_entry(ent), generated_summary)
            papers.append(paper)
        return papers

    def count_unchecked_papers(self) -> int:
        self.reader.update_feeds()
        entry_counts = self.reader.get_entry_counts(read=False)
        return entry_counts.total if entry_counts.total else 0
