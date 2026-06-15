import logging
import traceback

from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import (
    APIRouter,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Request,
    status,
    Query,
)

from app.core import get_db_session
from app.services import (
    ResumeService,
    ResumeAnalysisService,
    ResumeNotFoundError,
    ResumeParsingError,
    ResumeValidationError,
    JobNotFoundError,
    JobParsingError,
    ResumeKeywordExtractionError,
    JobKeywordExtractionError,
)
from app.schemas.pydantic import (
    ResumeImprovementRequest,
    ImprovedMarkdownRequest,
    ImprovedMarkdownResponse,
)
from app.utils.markdown_extractor import (
    extract_improved_markdown,
    build_fallback_markdown,
    count_sections,
)
from app.models import ProcessedResume

resume_router = APIRouter()
logger = logging.getLogger(__name__)


@resume_router.post(
    "/upload",
    summary="Upload a resume in PDF or DOCX format and store it into DB in HTML/Markdown format",
)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Accepts a PDF or DOCX file, converts it to HTML/Markdown, and stores it in the database.

    Raises:
        HTTPException: If the file type is not supported or if the file is empty.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))

    allowed_content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and DOCX files are allowed.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file. Please upload a valid file.",
        )

    try:
        resume_service = ResumeService(db)
        resume_id = await resume_service.convert_and_store_resume(
            file_bytes=file_bytes,
            file_type=file.content_type,
            filename=file.filename,
            content_type="md",
        )
    except ResumeValidationError as e:
        logger.warning(f"Resume validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Error processing file: {str(e)} - traceback: {traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}",
        )

    return {
        "message": f"File {file.filename} successfully processed as MD and stored in the DB",
        "request_id": request_id,
        "resume_id": resume_id,
    }


@resume_router.post(
    "/improve",
    summary="Score and improve a resume against a job description",
)
async def score_and_improve(
    request: Request,
    payload: ResumeImprovementRequest,
    db: AsyncSession = Depends(get_db_session),
    stream: bool = Query(
        False, description="Enable streaming response using Server-Sent Events"
    ),
):
    """
    Scores and improves a resume against a job description.

    Raises:
        HTTPException: If the resume or job is not found.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))
    headers = {"X-Request-ID": request_id}

    request_payload = payload.model_dump()

    try:
        resume_id = str(request_payload.get("resume_id", ""))
        if not resume_id:
            raise ResumeNotFoundError(
                message="invalid value passed in `resume_id` field, please try again with valid resume_id."
            )
        job_id = str(request_payload.get("job_id", ""))
        if not job_id:
            raise JobNotFoundError(
                message="invalid value passed in `job_id` field, please try again with valid job_id."
            )
        analysis_service = ResumeAnalysisService(db=db)

        if stream:
            return StreamingResponse(
                content=analysis_service.run_and_stream(
                    resume_id=resume_id,
                    job_id=job_id,
                ),
                media_type="text/event-stream",
                headers=headers,
            )
        else:
            analysis_result = await analysis_service.run(
                resume_id=resume_id,
                job_id=job_id,
            )
            return JSONResponse(
                content={
                    "request_id": request_id,
                    "data": analysis_result,
                },
                headers=headers,
            )
    except ResumeNotFoundError as e:
        logger.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except JobNotFoundError as e:
        logger.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except ResumeParsingError as e:
        logger.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except JobParsingError as e:
        logger.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except ResumeKeywordExtractionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except JobKeywordExtractionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error: {str(e)} - traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="sorry, something went wrong!",
        )


@resume_router.get(
    "",
    summary="Get resume data from both resume and processed_resume models",
)
async def get_resume(
    request: Request,
    resume_id: str = Query(..., description="Resume ID to fetch data for"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves resume data from both resume_model and processed_resume model by resume_id.

    Args:
        resume_id: The ID of the resume to retrieve

    Returns:
        Combined data from both resume and processed_resume models

    Raises:
        HTTPException: If the resume is not found or if there's an error fetching data.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))
    headers = {"X-Request-ID": request_id}

    try:
        if not resume_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="resume_id is required",
            )

        resume_service = ResumeService(db)
        resume_data = await resume_service.get_resume_with_processed_data(
            resume_id=resume_id
        )
        
        if not resume_data:
            raise ResumeNotFoundError(
                message=f"Resume with id {resume_id} not found"
            )

        return JSONResponse(
            content={
                "request_id": request_id,
                "data": resume_data,
            },
            headers=headers,
        )
    
    except ResumeNotFoundError as e:
        logger.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error fetching resume: {str(e)} - traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching resume data",
        )


@resume_router.post(
    "/improved-markdown",
    response_model=ImprovedMarkdownResponse,
    summary="Extract the optimized-resume markdown from a previous /improve result",
)
async def get_improved_markdown(
    request: Request,
    payload: ImprovedMarkdownRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Recover the "modified resume" code block produced by the HR-judge
    prompt (Step 4) so it can be fed straight into the a4cv visual editor.

    Strategy:
      1. Try to extract the first/largest ```md fenced block from the
         caller-supplied `analysis_result` text.
      2. If extraction fails (or the block doesn't look like a markdown
         document), rebuild a minimal a4cv-compatible markdown from the
         `processed_resumes` row stored in DB.
    """
    request_id = getattr(request.state, "request_id", str(uuid4()))
    headers = {"X-Request-ID": request_id}

    try:
        markdown, source = extract_improved_markdown(payload.analysis_result)
        if not markdown:
            logger.info(
                f"No ```md code block found in analysis_result for "
                f"resume_id={payload.resume_id}; falling back to ProcessedResume."
            )
            from sqlalchemy.future import select
            result = await db.execute(
                select(ProcessedResume).where(
                    ProcessedResume.resume_id == payload.resume_id
                )
            )
            processed_resume = result.scalars().first()
            if not processed_resume:
                raise ResumeNotFoundError(
                    message=f"Resume with id {payload.resume_id} not found"
                )
            markdown = build_fallback_markdown(processed_resume)
            source = "fallback"

        body = ImprovedMarkdownResponse(
            markdown=markdown,
            source=source,
            sections_detected=count_sections(markdown),
        )
        return JSONResponse(
            content={"request_id": request_id, "data": body.model_dump()},
            headers=headers,
        )
    except ResumeNotFoundError as e:
        logger.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Error extracting improved markdown: {str(e)} - "
            f"traceback: {traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error extracting improved markdown",
        )