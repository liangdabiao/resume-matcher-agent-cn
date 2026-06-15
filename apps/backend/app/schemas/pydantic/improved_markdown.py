from pydantic import BaseModel, Field


class ImprovedMarkdownRequest(BaseModel):
    """Request payload for extracting the 'improved resume' markdown from an
    existing analysis result produced by the HR-judge /improve endpoint.

    The caller (the frontend dashboard) supplies the full `analysis_result`
    text it already received, so the backend does not need to re-run the
    expensive LLM analysis.
    """

    resume_id: str = Field(..., description="Resume ID (matches /resumes/* endpoints)")
    job_id: str = Field(..., description="Job ID (matches /jobs/* endpoints)")
    analysis_result: str = Field(
        ...,
        description="Full markdown returned by the /improve endpoint",
    )


class ImprovedMarkdownResponse(BaseModel):
    """Response payload containing the optimized resume as a clean markdown
    string ready to be passed into the a4cv visual editor.
    """

    markdown: str = Field(..., description="The optimized resume in a4cv-compatible markdown")
    source: str = Field(
        ...,
        description='Either "extracted" (from a ```md code block in analysis_result) or "fallback" (rebuilt from processed_resume)',
    )
    sections_detected: int = Field(0, description="Number of `##` sections detected in the returned markdown")
