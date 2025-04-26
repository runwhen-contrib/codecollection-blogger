from typing import TypedDict, Dict, List, OrderedDict
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from codecollection_blogger.fetch_codecollection import TaskSourceCode


PARAGRAPH_TYPE_INTRO = "intro"
PARAGRAPH_TYPE_ISSUE = "issue"


@dataclass_json
@dataclass
class BasicIssue:
    """Basic issue information extracted from Robot Framework test code."""

    title: str
    details: str
    trigger_condition: str
    severity: str


@dataclass_json
@dataclass
class EnrichedIssue(BasicIssue):
    """Enriched issue with additional analysis from LLM."""

    problem_statement: str
    impact: str
    resolution: str
    revised_title: str

    @classmethod
    def from_dict_with_basic(cls, data: Dict[str, str], basic_issue: BasicIssue) -> "EnrichedIssue":
        return cls(
            title=basic_issue.title,
            details=basic_issue.details,
            trigger_condition=basic_issue.trigger_condition,
            severity=basic_issue.severity,
            problem_statement=data["problem_statement"],
            impact=data["impact"],
            resolution=data["resolution"],
            revised_title=data["revised_title"],
        )


@dataclass
class BlogParagraph:
    """A paragraph in the blog post with its type, header, and content."""

    paragraph_type: str
    header: str
    body: str


class BlogPostState(TypedDict):
    """State for the blog post generation workflow."""

    task: TaskSourceCode
    title: str
    slug: str
    blog_post: str
    raw_paragraphs: List[BlogParagraph]  # All paragraphs that might be included in final post
    enriched_issues: List[BasicIssue]  # List of enriched issues for analysis
