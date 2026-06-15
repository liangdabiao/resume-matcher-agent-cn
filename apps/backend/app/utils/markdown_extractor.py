"""Extracts the "improved resume" markdown block from the HR-judge analysis
output, with a structured-resume fallback for cases where the LLM did not
emit a parseable code block.

The HR-judge prompt template (app/prompt/hr_judge.py) Step 4 instructs the
LLM to put the optimized resume inside a ```md ... ``` fenced code block;
this module recovers that block.

The fallback path uses the structured JSON stored in ProcessedResume to
emit a minimal a4cv-compatible markdown (a4cv-main's parseMD expects
`# name`, `## section`, `### title | meta`, `- bullet`).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Match the FIRST fenced code block. Fence may be ``` or ```md / ```markdown.
_CODE_BLOCK_RE = re.compile(
    r"```(?:md|markdown)?[ \t]*\n([\s\S]+?)\n```",
    re.IGNORECASE,
)
# Detect a real markdown heading at the start of a line
_HEADING_RE = re.compile(r"^#{1,2}\s+\S+", re.MULTILINE)
# Count `## ` section headings
_SECTION_RE = re.compile(r"^##\s+\S+", re.MULTILINE)


def extract_improved_markdown(analysis_result: Optional[str]) -> Tuple[Optional[str], str]:
    """Try to pull the optimized-resume code block out of an HR-judge output.

    Returns:
        (markdown, source) where source is "extracted" or "none".
    """
    if not analysis_result:
        return None, "none"
    matches = _CODE_BLOCK_RE.findall(analysis_result)
    if not matches:
        return None, "none"
    # Prefer the longest block (the resume is usually the largest one)
    candidate = max(matches, key=len).strip()
    if not _HEADING_RE.search(candidate):
        # Not a markdown document (no `#`/`##` heading) — likely not the resume
        return None, "none"
    return candidate, "extracted"


def count_sections(markdown: str) -> int:
    if not markdown:
        return 0
    return len(_SECTION_RE.findall(markdown))


def _safe_json_loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def build_fallback_markdown(processed_resume) -> str:
    """Rebuild a minimal a4cv-compatible markdown from a ProcessedResume row.

    Used when the LLM did not emit a code block, so the editor at least has
    something to render.
    """
    pd = _safe_json_loads(processed_resume.personal_data, {}) or {}
    name = pd.get("name") or "你的姓名"
    title = pd.get("title") or pd.get("position") or ""

    contact_bits = []
    for key in ("email", "phone", "location"):
        v = pd.get(key)
        if v:
            contact_bits.append(str(v))
    for key in ("website", "linkedin", "github"):
        v = pd.get(key)
        if v:
            contact_bits.append(str(v))

    out = [f"# {name}"]
    if title:
        out.append(f"## {title}")
    if contact_bits:
        out.append("")
        out.append("> " + " · ".join(contact_bits))

    experiences = _safe_json_loads(processed_resume.experiences, {}).get("experiences", [])
    if experiences:
        out += ["", "## 工作经历"]
        for e in experiences:
            t = e.get("title") or e.get("position") or "职位"
            c = e.get("company") or ""
            p = e.get("period") or e.get("duration") or ""
            meta = " · ".join(x for x in (c, p) if x)
            out.append(f"### {t}" + (f" | {meta}" if meta else ""))
            for b in e.get("description") or e.get("bullets") or []:
                if b:
                    out.append(f"- {b}")

    projects = _safe_json_loads(processed_resume.projects, {}).get("projects", [])
    if projects:
        out += ["", "## 项目经历"]
        for p in projects:
            t = p.get("title") or p.get("name") or "项目"
            role = p.get("role") or ""
            period = p.get("period") or ""
            meta = " · ".join(x for x in (role, period) if x)
            out.append(f"### {t}" + (f" | {meta}" if meta else ""))
            for b in p.get("description") or p.get("bullets") or []:
                if b:
                    out.append(f"- {b}")

    education = _safe_json_loads(processed_resume.education, {}).get("education", [])
    if education:
        out += ["", "## 教育背景"]
        for ed in education:
            school = ed.get("school") or ed.get("institution") or "学校"
            degree = ed.get("degree") or ""
            period = ed.get("period") or ""
            meta = " · ".join(x for x in (degree, period) if x)
            out.append(f"### {school}" + (f" | {meta}" if meta else ""))

    skills_block = _safe_json_loads(processed_resume.skills, {}).get("skills", [])
    if skills_block:
        out += ["", "## 技能标签"]
        if isinstance(skills_block, list):
            names = [s.get("name") if isinstance(s, dict) else str(s) for s in skills_block]
            out.append(" · ".join(filter(None, names)))
        else:
            out.append(str(skills_block))

    achievements = _safe_json_loads(processed_resume.achievements, {}).get("achievements", [])
    if achievements:
        out += ["", "## 证书与荣誉"]
        for a in achievements:
            if isinstance(a, dict):
                t = a.get("title") or a.get("name") or "荣誉"
                out.append(f"- {t}")
            else:
                out.append(f"- {a}")

    research = _safe_json_loads(processed_resume.research_work, {}).get("research_work", [])
    if research:
        out += ["", "## 论文发表"]
        for r in research:
            if isinstance(r, dict):
                t = r.get("title") or r.get("name") or "论文"
                out.append(f"- {t}")
            else:
                out.append(f"- {r}")

    return "\n".join(out).rstrip() + "\n"
