import operator
from typing import Annotated, TypedDict, List, Literal
from pydantic import BaseModel, Field

class ReviewFinding(BaseModel):
    category: Literal["security", "performance", "logic_and_tests"]
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    file_path: str = Field(description="File path from the git diff")
    line_number: int = Field(description="Approximate line number in the diff")
    issue: str = Field(description="Clear explanation of the bug or vulnerability")
    suggested_fix: str = Field(description="Code snippet or actionable fix")

class NodeFindingsList(BaseModel):
    findings: List[ReviewFinding]

class PRReviewState(TypedDict):
    repo_full_name: str
    pr_number: int
    pr_title: str
    raw_diff: str
    findings: Annotated[List[ReviewFinding], operator.add]
    final_markdown_review: str
    # NEW: The Manager's dynamic queue!
    remaining_agents: List[str]