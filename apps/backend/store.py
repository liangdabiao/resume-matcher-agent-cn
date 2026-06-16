"""
JSON 文件存储。替代 SQLAlchemy + SQLite，零数据库依赖。

存储结构：
    data/resumes/<resume_id>.json   一个简历 = 一个文件（raw + processed 合并）
    data/jobs/<job_id>.json         一个 JD = 一个文件（raw + processed 合并）

设计要点（与旧版响应结构保持兼容）：
- 统一剥掉旧版 wrapper key（旧版 experiences 存 {"experiences":[...]}，这里直接存 [...]）
- 字段名用 snake_case（与旧版 model_dump 后入库的形态一致）
- 保留拼写陷阱 compensation_and_benfits（前端有兜底，不改）
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from config import RESUMES_DIR, JOBS_DIR


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_json(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 简历 ──────────────────────────────────────────────────────────────

def save_resume(content: str, processed: dict, content_type: str = "md") -> str:
    """保存简历（raw + processed 合并到一个文件），返回 resume_id。"""
    resume_id = str(uuid.uuid4())
    record = {
        "resume_id": resume_id,
        "content": content,
        "content_type": content_type,
        "created_at": _now_iso(),
        "processed": processed,
    }
    _write_json(os.path.join(RESUMES_DIR, f"{resume_id}.json"), record)
    return resume_id


def get_resume(resume_id: str) -> Optional[dict]:
    """读取简历完整记录。"""
    return _read_json(os.path.join(RESUMES_DIR, f"{resume_id}.json"))


def get_resume_view(resume_id: str) -> Optional[dict]:
    """
    构造 GET /resumes 的响应结构（与旧版 get_resume_with_processed_data 兼容）。
    """
    rec = get_resume(resume_id)
    if not rec:
        return None
    p = rec.get("processed") or {}
    return {
        "resume_id": rec["resume_id"],
        "raw_resume": {
            "id": 0,
            "content": rec.get("content", ""),
            "content_type": rec.get("content_type", "md"),
            "created_at": rec.get("created_at"),
        },
        "processed_resume": {
            "personal_data": p.get("personal_data"),
            "experiences": p.get("experiences"),
            "projects": p.get("projects"),
            "skills": p.get("skills"),
            "research_work": p.get("research_work"),
            "achievements": p.get("achievements"),
            "education": p.get("education"),
            "extracted_keywords": p.get("extracted_keywords"),
            "processed_at": p.get("processed_at"),
        },
    }


# ── 岗位 ──────────────────────────────────────────────────────────────

def save_job(resume_id: str, content: str, processed: dict) -> str:
    """保存 JD，返回 job_id。"""
    job_id = str(uuid.uuid4())
    record = {
        "job_id": job_id,
        "resume_id": resume_id,
        "content": content,
        "created_at": _now_iso(),
        "processed": processed,
    }
    _write_json(os.path.join(JOBS_DIR, f"{job_id}.json"), record)
    return job_id


def get_job(job_id: str) -> Optional[dict]:
    """读取 JD 完整记录。"""
    return _read_json(os.path.join(JOBS_DIR, f"{job_id}.json"))


def get_job_view(job_id: str) -> Optional[dict]:
    """
    构造 GET /jobs 的响应结构（与旧版 get_job_with_processed_data 兼容）。
    """
    rec = get_job(job_id)
    if not rec:
        return None
    p = rec.get("processed") or {}
    return {
        "job_id": rec["job_id"],
        "raw_job": {
            "id": 0,
            "resume_id": rec.get("resume_id"),
            "content": rec.get("content", ""),
            "created_at": rec.get("created_at"),
        },
        "processed_job": {
            "job_title": p.get("job_title"),
            "company_profile": p.get("company_profile"),
            "location": p.get("location"),
            "date_posted": p.get("date_posted"),
            "employment_type": p.get("employment_type"),
            "job_summary": p.get("job_summary"),
            "key_responsibilities": p.get("key_responsibilities"),
            "qualifications": p.get("qualifications"),
            # 注意拼写：保留旧版的 "benfits" 以兼容全链路
            "compensation_and_benfits": p.get("compensation_and_benfits"),
            "application_info": p.get("application_info"),
            "extracted_keywords": p.get("extracted_keywords"),
            "processed_at": p.get("processed_at"),
        },
    }


# ── 处理后的结构化数据规范化 ──────────────────────────────────────────
# LLM 返回的是驼峰键（jobTitle/companyProfile/...），这里转成 snake_case
# 统一存数组/对象（剥掉旧版 wrapper key），与 get_resume_view/get_job_view 对齐。

_CAMEL_RESUME_MAP = {
    "Personal Data": "personal_data",
    "Experiences": "experiences",
    "Projects": "projects",
    "Skills": "skills",
    "Research Work": "research_work",
    "Achievements": "achievements",
    "Education": "education",
    "Extracted Keywords": "extracted_keywords",
}

_CAMEL_JOB_MAP = {
    "jobTitle": "job_title",
    "companyProfile": "company_profile",
    "location": "location",
    "datePosted": "date_posted",
    "employmentType": "employment_type",
    "jobSummary": "job_summary",
    "keyResponsibilities": "key_responsibilities",
    "qualifications": "qualifications",
    "compensationAndBenefits": "compensation_and_benfits",
    "compensationAndBenfits": "compensation_and_benfits",
    "applicationInfo": "application_info",
    "extractedKeywords": "extracted_keywords",
}


def normalize_resume_structured(raw: dict) -> dict:
    """
    把 LLM 返回的结构化简历（带空格/驼峰键）归一化成 snake_case 存储格式。
    容错：LLM 可能返回 jobTitle 也可能返回 job_title，两种都接受。
    """
    out = {}
    for raw_key, std_key in _CAMEL_RESUME_MAP.items():
        val = raw.get(raw_key)
        if val is None:
            # 兼容已经是 snake_case 的返回
            val = raw.get(std_key)
        out[std_key] = val
    out["processed_at"] = _now_iso()
    return out


def normalize_job_structured(raw: dict) -> dict:
    """把 LLM 返回的结构化 JD 归一化成存储格式。"""
    out = {}
    for raw_key, std_key in _CAMEL_JOB_MAP.items():
        if std_key in out:
            continue
        val = raw.get(raw_key)
        if val is None:
            val = raw.get(std_key)
        out[std_key] = val
    out["processed_at"] = _now_iso()
    return out
