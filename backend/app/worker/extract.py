"""Turn crawled pages into structured features and a navigation graph (deterministic)."""

import re

from ..ids import slug
from ..schemas import CrawledElement, CrawledInteraction, CrawledPage, FeatureElement, FeatureSpec, NavEdgeSpec

STOPWORDS = {"the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "page", "new", "create", "add", "manage", "your", "with", "this"}


def clean_title(title: str) -> str:
    """'Reports — Lumen' -> 'Reports'."""
    return re.split(r"\s+[—|–-]\s+", title)[0].strip() or title.strip()


def humanize_path(path: str) -> str:
    """'/web/index.php/pim/viewEmployeeList' -> 'View Employee List'."""
    segment = [p for p in path.split("/") if p and not p.endswith(".php")][-1:] or ["Home"]
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", segment[0]).replace("-", " ").replace("_", " ")
    return words[:1].upper() + words[1:]


GREETING_RE = re.compile(r"^(good (morning|afternoon|evening)|welcome|hello|hi)\b", re.I)


def page_name(page: CrawledPage, shared_title: bool = False) -> str:
    """Visible heading first (unless it is a greeting like 'Good morning, Aryan'); the document title only if it is specific to the page; else the URL path."""
    heading = next((h.strip() for h in page.headings if not GREETING_RE.match(h.strip())), "")
    if heading:
        return heading
    title = clean_title(page.title)
    return title if title and not shared_title else humanize_path(page.path)


def page_description(page: CrawledPage, name: str) -> str:
    lines = [l.strip() for l in page.text.splitlines() if l.strip()]
    for line in lines:
        if line != name and 30 <= len(line) <= 300 and line.endswith((".", "!")):
            return line
    return f"The {name} page."


def action_name(label: str) -> str:
    label = re.sub(r"\s+", " ", re.sub(r"^[^A-Za-z0-9]+", "", label)).strip()  # drop leading icons like '+'
    label = re.sub(r"^(New|Add)\b", "Create", label, flags=re.I)
    return label[:1].upper() + label[1:]


def keywords(*texts: str) -> list[str]:
    words: list[str] = []
    for text in texts:
        for w in re.findall(r"[a-z0-9]+", text.lower()):
            if w not in STOPWORDS and w not in words:
                words.append(w)
    return words


def _nav_labels(pages: list[CrawledPage]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for page in pages:
        for el in page.elements:
            if el.tag == "a" and el.href and el.in_nav and el.href not in labels and el.text:
                labels[el.href] = el.text.split("\n")[0]
    return labels


def _nav_path(path: str, nav_labels: dict[str, str], fallback: str) -> list[str]:
    parts = [p for p in path.split("/") if p]
    prefixes = ["/" + "/".join(parts[: i + 1]) for i in range(len(parts))] or ["/"]
    labels = [nav_labels[p] for p in prefixes if p in nav_labels]
    return labels or [fallback]


def _elements_for_page(page: CrawledPage) -> list[FeatureElement]:
    out: list[FeatureElement] = []
    for el in page.elements:
        if el.in_nav:
            continue
        role = "trigger" if el.tag == "button" else "input" if el.input_type else "link" if el.tag == "a" else "other"
        out.append(FeatureElement(name=el.text or el.testid or el.selector, selector=el.selector, role=role))
    return out[:20]


def _inputs(elements: list[CrawledElement]) -> list[FeatureElement]:
    """Form inputs of a page/reveal, excluding header/sidebar widgets (global search boxes etc.)."""
    return [
        FeatureElement(name=e.text or e.placeholder or e.testid or f"{e.input_type} field", selector=e.selector, role="input")
        for e in elements if e.input_type and not e.in_nav
    ]


GLOBAL_CONTROL_MIN_PAGES = 3


def _global_controls(pages: list[CrawledPage]) -> set[str]:
    """Button labels that appear (with an effect) on many pages are site-wide controls, not per-page features."""
    counts: dict[str, int] = {}
    for page in pages:
        for label in {i.label for i in page.interactions if i.revealed or i.navigates_to}:
            counts[label] = counts.get(label, 0) + 1
    return {label for label, n in counts.items() if n >= GLOBAL_CONTROL_MIN_PAGES}


def _action_feature(page: CrawledPage, inter: CrawledInteraction, pages_by_path: dict[str, CrawledPage], nav_labels: dict[str, str], pname: str, site_wide: bool = False) -> FeatureSpec:
    name = action_name(inter.label)
    if len(name.split()) == 1 and not site_wide:  # "Search", "Create", "View" are meaningless without their page
        name = f"{name} {pname}" if name.lower() not in pname.lower() else pname
    trigger = FeatureElement(name=inter.label, selector=inter.selector, role="trigger")
    if inter.navigates_to and inter.navigates_to in pages_by_path:
        target = pages_by_path[inter.navigates_to]
        inputs = _inputs(target.elements)
        route = inter.navigates_to
        opens = f", which opens the {page_name(target, True)} page"
    else:
        inputs = _inputs(inter.revealed)
        route = page.path
        opens = ""
    verb = name.lower()
    fields = ", ".join(i.name.lower() for i in inputs[:4])
    where = "any page" if site_wide else f"the {pname} page"
    description = f"On {where}, click '{inter.label}'{opens}" + (f" and fill in {fields}." if fields else ".")
    return FeatureSpec(
        name=name, slug=slug(name), kind="action", description=description, route=route, page_path=page.path,
        nav_path=_nav_path(page.path, nav_labels, pname) + [inter.label],
        elements=[trigger, *inputs],
        questions=[f"How do I {verb}?", f"Can I {verb}?", f"Where can I {verb}?", f"Show me how to {verb}."],
        keywords=keywords(name, inter.label, pname, *(i.name for i in inputs)),
    )


def meaningful(inter: CrawledInteraction, pages_by_path: dict[str, CrawledPage]) -> bool:
    """An interaction is a feature if it navigates to a known page or reveals form inputs."""
    if inter.navigates_to:
        return inter.navigates_to in pages_by_path
    return any(e.input_type for e in inter.revealed)


def extract_features(pages: list[CrawledPage]) -> tuple[list[FeatureSpec], list[NavEdgeSpec]]:
    nav_labels = _nav_labels(pages)
    pages_by_path = {p.path: p for p in pages}
    titles = [clean_title(p.title) for p in pages]
    shared_title = len(pages) > 1 and len(set(titles)) < len(titles)  # e.g. every page titled "OrangeHRM"
    features: dict[str, FeatureSpec] = {}
    edges: list[NavEdgeSpec] = []
    global_controls = _global_controls(pages)
    seen_global: set[str] = set()

    for page in pages:
        pname = page_name(page, shared_title)
        nav_path = _nav_path(page.path, nav_labels, pname)
        spec = FeatureSpec(
            name=pname, slug=slug(pname), kind="page", description=page_description(page, pname), route=page.path, page_path=page.path,
            nav_path=nav_path, elements=_elements_for_page(page),
            questions=[f"Does this product have {pname.lower()}?", f"What does the {pname} page show?", f"Where can I find {pname.lower()}?", f"Take me to {pname.lower()}."],
            keywords=keywords(pname, page.path, *page.headings[:5]),
        )
        features.setdefault(spec.slug, spec)

        for el in page.elements:
            if el.tag == "a" and el.href and el.href != page.path:
                edges.append(NavEdgeSpec(from_path=page.path, to_path=el.href, selector=el.selector, label=el.text))
        for inter in page.interactions:
            if inter.navigates_to:
                edges.append(NavEdgeSpec(from_path=page.path, to_path=inter.navigates_to, selector=inter.selector, label=inter.label))
            if not meaningful(inter, pages_by_path):
                continue
            if inter.label in global_controls:  # site-wide control (theme switcher, feedback…): one feature, on the first page it appears
                if inter.label in seen_global:
                    continue
                seen_global.add(inter.label)
                action = _action_feature(page, inter, pages_by_path, nav_labels, pname, site_wide=True)
            else:
                action = _action_feature(page, inter, pages_by_path, nav_labels, pname)
            features[action.slug] = action  # an action beats a same-named page: its demo is richer and its route still navigates there

    unique_edges = {(e.from_path, e.to_path, e.selector): e for e in edges}
    return list(features.values()), list(unique_edges.values())
