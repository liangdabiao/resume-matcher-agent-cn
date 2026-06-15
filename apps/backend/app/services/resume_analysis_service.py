import gc
import json
import logging
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, AsyncGenerator, Tuple

from app.prompt import prompt_factory
from app.agent import AgentManager
from app.models import Resume, Job, ProcessedResume, ProcessedJob
from .exceptions import (
    ResumeNotFoundError,
    JobNotFoundError,
    ResumeParsingError,
    JobParsingError,
    ResumeKeywordExtractionError,
    JobKeywordExtractionError,
)

logger = logging.getLogger(__name__)


class ResumeAnalysisService:
    """
    Service to analyze a resume against a job description using a single LLM
    call (hr_judge prompt). Replaces the original iterative
    embedding/cosine-similarity scoring loop from upstream.
    """

    def __init__(self, db: AsyncSession):
        logger.debug(f"Initializing ResumeAnalysisService")
        self.db = db
        self.md_agent_manager = AgentManager(strategy="md")
        self.json_agent_manager = AgentManager()
        logger.debug("ResumeAnalysisService initialized successfully")

    def _validate_resume_keywords(
        self, processed_resume: ProcessedResume, resume_id: str
    ) -> None:
        """
        Validates that keyword extraction was successful for a resume.
        Raises ResumeKeywordExtractionError if keywords are missing or empty.
        """
        logger.debug(f"Validating resume keywords for resume_id={resume_id}")
        if not processed_resume.extracted_keywords:
            logger.error(f"No extracted keywords found for resume_id={resume_id}")
            raise ResumeKeywordExtractionError(resume_id=resume_id)

        try:
            keywords_data = json.loads(processed_resume.extracted_keywords)
            logger.debug(f"Successfully parsed keywords data for resume_id={resume_id}")
            keywords = keywords_data.get("extracted_keywords", [])
            if not keywords or len(keywords) == 0:
                logger.error(f"Extracted keywords list is empty for resume_id={resume_id}")
                raise ResumeKeywordExtractionError(resume_id=resume_id)
            logger.debug(f"Validated {len(keywords)} keywords for resume_id={resume_id}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for resume keywords (resume_id={resume_id}): {e}")
            raise ResumeKeywordExtractionError(resume_id=resume_id)

    def _validate_job_keywords(self, processed_job: ProcessedJob, job_id: str) -> None:
        """
        Validates that keyword extraction was successful for a job.
        Raises JobKeywordExtractionError if keywords are missing or empty.
        """
        logger.debug(f"Validating job keywords for job_id={job_id}")
        if not processed_job.extracted_keywords:
            logger.error(f"No extracted keywords found for job_id={job_id}")
            raise JobKeywordExtractionError(job_id=job_id)

        try:
            keywords_data = json.loads(processed_job.extracted_keywords)
            logger.debug(f"Successfully parsed keywords data for job_id={job_id}")
            keywords = keywords_data.get("extracted_keywords", [])
            if not keywords or len(keywords) == 0:
                logger.error(f"Extracted keywords list is empty for job_id={job_id}")
                raise JobKeywordExtractionError(job_id=job_id)
            logger.debug(f"Validated {len(keywords)} keywords for job_id={job_id}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for job keywords (job_id={job_id}): {e}")
            raise JobKeywordExtractionError(job_id=job_id)

    async def _get_resume(
        self, resume_id: str
    ) -> Tuple[Resume | None, ProcessedResume | None]:
        """
        Fetches the resume from the database.
        """
        logger.debug(f"Fetching resume with resume_id={resume_id} from database")
        query = select(Resume).where(Resume.resume_id == resume_id)
        result = await self.db.execute(query)
        resume = result.scalars().first()

        if not resume:
            logger.error(f"Resume not found for resume_id={resume_id}")
            raise ResumeNotFoundError(resume_id=resume_id)
        logger.debug(f"Found resume with resume_id={resume_id}, title={resume.title if hasattr(resume, 'title') else 'N/A'}")

        query = select(ProcessedResume).where(ProcessedResume.resume_id == resume_id)
        result = await self.db.execute(query)
        processed_resume = result.scalars().first()

        if not processed_resume:
            logger.error(f"Processed resume not found for resume_id={resume_id}")
            raise ResumeParsingError(resume_id=resume_id)
        logger.debug(f"Found processed resume for resume_id={resume_id}")

        self._validate_resume_keywords(processed_resume, resume_id)

        return resume, processed_resume

    async def _get_job(self, job_id: str) -> Tuple[Job | None, ProcessedJob | None]:
        """
        Fetches the job from the database.
        """
        logger.debug(f"Fetching job with job_id={job_id} from database")
        query = select(Job).where(Job.job_id == job_id)
        result = await self.db.execute(query)
        job = result.scalars().first()

        if not job:
            logger.error(f"Job not found for job_id={job_id}")
            raise JobNotFoundError(job_id=job_id)
        logger.debug(f"Found job with job_id={job_id}, title={job.title if hasattr(job, 'title') else 'N/A'}")

        query = select(ProcessedJob).where(ProcessedJob.job_id == job_id)
        result = await self.db.execute(query)
        processed_job = result.scalars().first()

        if not processed_job:
            logger.error(f"Processed job not found for job_id={job_id}")
            raise JobParsingError(job_id=job_id)
        logger.debug(f"Found processed job for job_id={job_id}")

        self._validate_job_keywords(processed_job, job_id)

        return job, processed_job




    async def run(self, resume_id: str, job_id: str) -> Dict:
        """
        Main method to run the scoring and improving process and return dict.
        Modified to use hr_judge.py prompt template for analysis instead of resume improvement.
        """
        logger.info(f"Starting ResumeAnalysisService.run for resume_id={resume_id}, job_id={job_id}")

        try:
            resume, processed_resume = await self._get_resume(resume_id)
            job, processed_job = await self._get_job(job_id)

            # Get the hr_judge prompt template
            logger.info("Getting hr_judge prompt template")
            prompt_template = prompt_factory.get("hr_judge")
            if not prompt_template:
                logger.error("Failed to get hr_judge prompt template")
                raise Exception("Failed to get hr_judge prompt template")

            # Format the prompt with resume and job data
            logger.info("Formatting prompt with resume and job data")
            formatted_prompt = prompt_template.format(
                Job_Description=job.content,
                raw_resume=resume.content,
                datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            logger.debug(f"Generated prompt length: {len(formatted_prompt)} characters")
            
            # Run the analysis using the MD agent manager
            logger.info("Running analysis with LLM")
            analysis_result = await self.md_agent_manager.run(formatted_prompt)
            logger.info("Analysis completed successfully")

            execution = {
                "resume_id": resume_id,
                "job_id": job_id,
                "analysis_result": analysis_result,
                "details": "Analysis completed successfully using hr_judge prompt template",
                "commentary": "The resume has been analyzed against the job description using the hr_judge prompt template."
            }

            logger.info(f"Final execution result: {execution}")

            gc.collect()

            return execution
        except Exception as e:
            import traceback
            logger.error(f"Error in ResumeAnalysisService.run: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return a default structure with all required fields even in case of error
            return {
                "resume_id": resume_id,
                "job_id": job_id,
                "analysis_result": "Error processing resume",
                "details": "An error occurred while processing your resume. Please try again.",
                "commentary": "We encountered an issue while analyzing your resume. Please make sure your resume is properly formatted and try again."
            }


    async def run_and_stream(self, resume_id: str, job_id: str, request_id: str = "") -> AsyncGenerator:
        """
        Main method to run the scoring and improving process and return dict.
        Modified to use hr_judge.py prompt template for analysis instead of resume improvement.
        """
        logger.info(f"Starting ScoreImprovementService.run_and_stream for resume_id={resume_id}, job_id={job_id}")

        try:
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Analyzing resume and job description...'})}\n\n"

            resume, processed_resume = await self._get_resume(resume_id)
            job, processed_job = await self._get_job(job_id)
            logger.debug("Successfully fetched resume and job data")

            yield f"data: {json.dumps({'status': 'parsing', 'message': 'Preparing analysis with hr_judge prompt...'})}\n\n"

            # Get the hr_judge prompt template
            logger.info("Getting hr_judge prompt template")
            prompt_template = prompt_factory.get("hr_judge")
            if not prompt_template:
                logger.error("Failed to get hr_judge prompt template")
                raise Exception("Failed to get hr_judge prompt template")

            # Format the prompt with resume and job data
            logger.info("Formatting prompt with resume and job data")
            formatted_prompt = prompt_template.format(
                Job_Description=job.content,
                raw_resume=resume.content,
                datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            logger.debug(f"Generated prompt length: {len(formatted_prompt)} characters")

            yield f"data: {json.dumps({'status': 'analyzing', 'message': 'Running analysis with LLM...'})}\n\n"

            # Run the analysis using the MD agent manager
            logger.info("Running analysis with LLM")
            analysis_result = await self.md_agent_manager.run(formatted_prompt)
            logger.info("Analysis completed successfully")

            final_result = {
                "resume_id": resume_id,
                "job_id": job_id,
                "analysis_result": analysis_result,
                "details": "Analysis completed successfully using hr_judge prompt template",
                "commentary": "The resume has been analyzed against the job description using the hr_judge prompt template.",
            }
            logger.info(f"Final result: {final_result}")

            # Wrap in {request_id, data: ...} so the SSE `completed` event
            # matches the shape of the non-streaming /improve response.
            yield f"data: {json.dumps({'status': 'completed', 'result': {'request_id': request_id, 'data': final_result}})}\n\n"
        except Exception as e:
            logger.error(f"Error in ScoreImprovementService.run_and_stream: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # 流式传输错误信息
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
