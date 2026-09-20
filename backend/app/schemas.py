"""Pydantic models shared across API, worker, and agent boundaries."""

from typing import Literal

from pydantic import BaseModel, Field

ActionType = Literal["navigate", "click", "highlight", "scroll", "type", "wait", "explain"]


class DemoAction(BaseModel):
    """A typed, code-free instruction for the host page bridge."""

    type: ActionType
    selector: str | None = None
    path: str | None = None
    value: str | None = None
    message: str | None = None
    ms: int | None = None
    label: str | None = None  # human name of the target (for status text)


class LoginConfig(BaseModel):
    """How the crawler signs in before discovery (for products behind a login page)."""

    url: str
    username: str
    password: str
    username_selector: str = "input[name='username']"
    password_selector: str = "input[name='password']"
    submit_selector: str = "button[type='submit']"


# ---- Crawl output -----------------------------------------------------------------


class CrawledElement(BaseModel):
    tag: str
    text: str = ""
    selector: str
    testid: str = ""
    href: str = ""  # same-origin path for links
    input_type: str = ""
    placeholder: str = ""
    in_nav: bool = False


class CrawledInteraction(BaseModel):
    """Result of clicking an action button during discovery."""

    selector: str
    label: str
    navigates_to: str = ""
    revealed: list[CrawledElement] = Field(default_factory=list)


class CrawledPage(BaseModel):
    url: str
    path: str
    title: str
    headings: list[str] = Field(default_factory=list)
    text: str = ""
    elements: list[CrawledElement] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    interactions: list[CrawledInteraction] = Field(default_factory=list)


# ---- Knowledge --------------------------------------------------------------------


class FeatureElement(BaseModel):
    name: str
    selector: str
    role: Literal["trigger", "input", "nav", "link", "other"] = "other"


class FeatureSpec(BaseModel):
    name: str
    slug: str
    kind: Literal["page", "action"]
    description: str
    route: str
    page_path: str
    nav_path: list[str]
    elements: list[FeatureElement]
    questions: list[str]
    keywords: list[str]


class NavEdgeSpec(BaseModel):
    from_path: str
    to_path: str
    selector: str
    label: str


class QnASpec(BaseModel):
    feature_slug: str = ""
    question: str
    answer: str


class DemoFlowSpec(BaseModel):
    feature_slug: str
    name: str
    description: str
    steps: list[DemoAction]


# ---- API --------------------------------------------------------------------------


class ProductCreate(BaseModel):
    name: str
    url: str
    id: str | None = None
    login: LoginConfig | None = None


class ProductOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    url: str
    description: str
    status: str
    requires_login: bool
    counts: dict[str, int]
    snippet: str


class JobOut(BaseModel):
    id: str
    status: str
    stage: str
    progress: float
    message: str
    stats: dict[str, int]
    updated_at: str


class ChatRequest(BaseModel):
    product_id: str
    session_id: str
    message: str


class DemoRunOut(BaseModel):
    id: str
    title: str
    total_steps: int


class ChatResponse(BaseModel):
    reply: str
    intent: str
    demo_run: DemoRunOut | None = None
    suggestions: list[str] = Field(default_factory=list)


class StepResult(BaseModel):
    ok: bool
    error: str = ""


class AdvanceRequest(BaseModel):
    result: StepResult | None = None


class AdvanceResponse(BaseModel):
    done: bool
    status: str
    step_index: int
    total_steps: int
    action: DemoAction | None = None
    message: str = ""
