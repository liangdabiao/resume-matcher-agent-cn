"""
Flask 后端应用。极简化重构，替代旧版 FastAPI + SQLAlchemy + Agent 抽象层。

路由契约与旧版 100% 兼容（前端零改动）：
    GET  /ping                                  健康检查
    POST /api/v1/resumes/upload                 上传简历（multipart）
    POST /api/v1/resumes/improve                分析简历（?stream=true 走 SSE）
    GET  /api/v1/resumes?resume_id=             获取简历
    POST /api/v1/resumes/improved-markdown      提取优化后简历 markdown
    POST /api/v1/jobs/upload                    上传 JD（JSON，手动校验 Content-Type）
    GET  /api/v1/jobs?job_id=                   获取 JD

启动：gunicorn app:app（宝塔/生产）或 python run.py（本地）。
"""
import json
import logging
import re
import uuid
from datetime import datetime

from flask import Flask, request, jsonify, Response, stream_with_context

import config
from config import ALLOWED_ORIGINS
import store
import llm
import parser as doc_parser
from prompts import (
    PROMPT_STRUCTURED_RESUME,
    PROMPT_STRUCTURED_JOB,
    PROMPT_HR_JUDGE,
    SCHEMA_STRUCTURED_RESUME,
    SCHEMA_STRUCTURED_JOB,
)

# ── 日志（标准库，去掉复杂轮转）──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if config.ENV == "production" else logging.DEBUG,
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("resume-matcher")

# ── 生产环境启动校验 ─────────────────────────────────────────────────
config.check_production()

app = Flask(__name__)


# ── CORS（after_request，简单可靠）──────────────────────────────────
@app.after_request
def _cors(resp: Response) -> Response:
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "*"
    return resp


# ── CORS 预检：Flask 默认对未注册 OPTIONS 返回 405，
#    浏览器在跨域 + Content-Type: application/json 场景下会先发预检，
#    没有这个处理器整个跨域 POST 都会被拦截。
@app.before_request
def _preflight():
    if request.method == "OPTIONS":
        resp = Response()
        origin = request.headers.get("Origin")
        if origin and origin in ALLOWED_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            req_methods = request.headers.get("Access-Control-Request-Method")
            resp.headers["Access-Control-Allow-Methods"] = req_methods or "GET,POST,OPTIONS"
            req_headers = request.headers.get("Access-Control-Request-Headers")
            resp.headers["Access-Control-Allow-Headers"] = req_headers or "*"
        return resp


# ── 统一错误类型：替代 _do_improve 的 (jsonify, status) tuple 模式 ────
class ApiError(Exception):
    """业务可主动抛的 HTTP 错误。message / status / service 用于响应构造。"""

    def __init__(self, message: str, status: int = 400, service: str = "api"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.service = service


@app.errorhandler(ApiError)
def _handle_api_error(e: ApiError):
    return _err(e.message, e.status, e.service)


# ── request_id 工具（与旧版格式兼容：服务段:uuid）────────────────────
def _request_id(service: str = "api") -> str:
    return f"{service}:{uuid.uuid4()}"


def _err(detail: str, status: int, service: str = "api"):
    """统一错误响应：{detail, request_id}"""
    return jsonify({"detail": detail, "request_id": _request_id(service)}), status


# ════════════════════════════════════════════════════════════════════
# 健康检查
# ════════════════════════════════════════════════════════════════════
@app.get("/ping")
def ping():
    return jsonify({"message": "pong", "database": "reachable"})


# ════════════════════════════════════════════════════════════════════
# 简历接口
# ════════════════════════════════════════════════════════════════════
@app.post("/api/v1/resumes/upload")
def upload_resume():
    """上传 PDF/DOCX 简历，解析文本 + LLM 结构化，存 JSON。"""
    rid = _request_id("resumes")

    f = request.files.get("file")
    if not f or not f.filename:
        return _err("No file provided", 400, "resumes")

    content_type = f.mimetype or f.content_type
    file_bytes = f.read()

    # 1. 提取文本
    try:
        text = doc_parser.extract_text_from_file(file_bytes, content_type)
    except ValueError as e:
        logger.warning(f"resume parse failed: {e}")
        return _err(str(e), 400, "resumes")
    except Exception as e:
        logger.error(f"resume parse error: {e}", exc_info=True)
        return _err(f"File conversion failed: {e}", 400, "resumes")

    # 2. LLM 结构化抽取（失败不阻断，processed 留空，前端有兜底）
    processed = {}
    try:
        prompt = PROMPT_STRUCTURED_RESUME.format(
            json.dumps(SCHEMA_STRUCTURED_RESUME, indent=2), text
        )
        raw = llm.call_llm(prompt, expect_json=True)
        processed = store.normalize_resume_structured(raw)
    except Exception as e:
        logger.error(f"resume structured extraction failed: {e}", exc_info=True)

    # 3. 存储
    resume_id = store.save_resume(content=text, processed=processed)

    return jsonify(
        {
            "message": "Resume uploaded and processed as MD successfully",
            "request_id": rid,
            "resume_id": resume_id,
        }
    )


@app.post("/api/v1/resumes/improve")
def improve_resume():
    """分析简历 vs JD。?stream=true 走 SSE 流式。"""
    rid = _request_id("resumes")
    stream = request.args.get("stream", "false").lower() in ("true", "1", "yes")

    data = request.get_json(silent=True) or {}
    resume_id = data.get("resume_id")
    job_id = data.get("job_id")
    if not resume_id or not job_id:
        return _err("resume_id and job_id are required", 422, "resumes")

    if stream:
        return Response(
            stream_with_context(_improve_stream(resume_id, job_id, rid)),
            mimetype="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # 非流式：异常走全局 errorhandler，类型安全
    result = _do_improve(resume_id, job_id, rid)
    return jsonify({"request_id": rid, "data": result})


def _do_improve(resume_id: str, job_id: str, rid: str) -> dict:
    """
    执行分析（核心逻辑，非流式与流式共用）。
    成功返回 dict；失败抛 ApiError，由全局 errorhandler 统一序列化。
    """
    resume = store.get_resume(resume_id)
    if not resume:
        raise ApiError(f"Resume not found: {resume_id}", 404, "resumes")
    job = store.get_job(job_id)
    if not job:
        raise ApiError(f"Job not found: {job_id}", 404, "resumes")

    try:
        prompt = PROMPT_HR_JUDGE.format(
            Job_Description=job.get("content", ""),
            raw_resume=resume.get("content", ""),
            datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        analysis_result = llm.call_llm(prompt, expect_json=False)
    except ApiError:
        raise
    except Exception as e:
        logger.error(f"improve LLM call failed: {e}", exc_info=True)
        raise ApiError(f"Analysis failed: {e}", 500, "resumes") from e

    return {
        "resume_id": resume_id,
        "job_id": job_id,
        "analysis_result": analysis_result,
        "details": "Analysis completed successfully using hr_judge prompt template.",
        "commentary": "The resume has been analyzed against the job description using the hr_judge prompt template.",
    }


def _improve_stream(resume_id: str, job_id: str, rid: str):
    """SSE 生成器。严格照搬旧版事件格式：data: {json}\\n\\n"""
    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    try:
        yield sse({"status": "starting", "message": "Analyzing resume and job description..."})

        resume = store.get_resume(resume_id)
        if not resume:
            yield sse({"status": "error", "message": f"Resume not found: {resume_id}"})
            return
        job = store.get_job(job_id)
        if not job:
            yield sse({"status": "error", "message": f"Job not found: {job_id}"})
            return

        yield sse({"status": "parsing", "message": "Preparing analysis with hr_judge prompt..."})

        prompt = PROMPT_HR_JUDGE.format(
            Job_Description=job.get("content", ""),
            raw_resume=resume.get("content", ""),
            datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        yield sse({"status": "analyzing", "message": "Running analysis with LLM..."})

        analysis_result = llm.call_llm(prompt, expect_json=False)

        final_result = {
            "resume_id": resume_id,
            "job_id": job_id,
            "analysis_result": analysis_result,
            "details": "Analysis completed successfully using hr_judge prompt template.",
            "commentary": "The resume has been analyzed against the job description using the hr_judge prompt template.",
        }
        # completed 的 result 双层包装，与非流式响应同构
        yield sse({"status": "completed", "result": {"request_id": rid, "data": final_result}})
    except Exception as e:
        logger.error(f"improve stream failed: {e}", exc_info=True)
        yield sse({"status": "error", "message": str(e)})


@app.get("/api/v1/resumes")
def get_resume():
    """获取简历 + 结构化数据。"""
    rid = _request_id("resumes")
    resume_id = request.args.get("resume_id")
    if not resume_id:
        return _err("resume_id is required", 422, "resumes")

    view = store.get_resume_view(resume_id)
    if not view:
        return _err(f"Resume not found: {resume_id}", 404, "resumes")
    return jsonify({"request_id": rid, "data": view})


@app.post("/api/v1/resumes/improved-markdown")
def improved_markdown():
    """
    从分析结果里提取优化后的简历 markdown（给 a4cv 编辑器用）。
    先正则抽 ```md 块；抽不到则从结构化简历拼兜底 markdown。
    """
    rid = _request_id("resumes")
    data = request.get_json(silent=True) or {}
    analysis_result = data.get("analysis_result") or ""
    resume_id = data.get("resume_id")

    # 1. 尝试从分析文本抽代码块
    md, source = _extract_md_block(analysis_result)
    if md:
        md = _normalize_md_for_a4cv(md)  # 加粗小节标题转 ##，让 a4cv 能识别结构
        return jsonify(
            {
                "request_id": rid,
                "data": {
                    "markdown": md,
                    "source": "extracted",
                    "sections_detected": _count_sections(md),
                },
            }
        )

    # 2. 兜底：从结构化简历拼装
    if resume_id:
        view = store.get_resume_view(resume_id)
        processed = view.get("processed_resume") if view else None
        if processed:
            md = _normalize_md_for_a4cv(_build_fallback_markdown(processed))
            return jsonify(
                {
                    "request_id": rid,
                    "data": {
                        "markdown": md,
                        "source": "fallback",
                        "sections_detected": _count_sections(md),
                    },
                }
            )

    return jsonify(
        {
            "request_id": rid,
            "data": {"markdown": "", "source": "none", "sections_detected": 0},
        }
    )


# ════════════════════════════════════════════════════════════════════
# 岗位接口
# ════════════════════════════════════════════════════════════════════
@app.post("/api/v1/jobs/upload")
def upload_job():
    """上传 JD（可批量）。手动校验 Content-Type 必须是 application/json。"""
    rid = _request_id("jobs")

    # 手动 Content-Type 校验（照搬旧版）
    ctype = request.headers.get("Content-Type", "")
    if "application/json" not in ctype:
        return _err("Content-Type must be application/json", 400, "jobs")

    data = request.get_json(silent=True) or {}
    resume_id = data.get("resume_id")
    job_descriptions = data.get("job_descriptions") or []

    if not resume_id:
        return _err("resume_id is required", 422, "jobs")
    if not job_descriptions:
        return _err("job_descriptions is required", 422, "jobs")

    # 校验 resume 存在
    if not store.get_resume(resume_id):
        return _err(f"resume corresponding to resume_id: {resume_id} not found", 400, "jobs")

    job_ids = []
    for desc in job_descriptions:
        # LLM 结构化
        processed = {}
        try:
            prompt = PROMPT_STRUCTURED_JOB.format(
                json.dumps(SCHEMA_STRUCTURED_JOB, indent=2), desc
            )
            raw = llm.call_llm(prompt, expect_json=True)
            processed = store.normalize_job_structured(raw)
        except Exception as e:
            logger.error(f"job structured extraction failed: {e}", exc_info=True)

        jid = store.save_job(resume_id=resume_id, content=desc, processed=processed)
        job_ids.append(jid)
        logger.info(f"Job created: {jid}")

    return jsonify(
        {
            "message": "data successfully processed",
            "job_id": job_ids,
            "request": {"request_id": rid, "payload": data},
        }
    )


@app.get("/api/v1/jobs")
def get_job():
    """获取 JD + 结构化数据。"""
    rid = _request_id("jobs")
    job_id = request.args.get("job_id")
    if not job_id:
        return _err("job_id is required", 422, "jobs")

    view = store.get_job_view(job_id)
    if not view:
        return _err(f"Job not found: {job_id}", 404, "jobs")
    return jsonify({"request_id": rid, "data": view})


# ════════════════════════════════════════════════════════════════════
# markdown 提取工具（照搬旧版 markdown_extractor.py 逻辑）
# ════════════════════════════════════════════════════════════════════
_CODE_BLOCK_RE = re.compile(r"```(?:md|markdown)?[ \t]*\n([\s\S]+?)\n```", re.IGNORECASE)
_HEADING_RE = re.compile(r"^#{1,2}\s+\S+", re.MULTILINE)
_SECTION_RE = re.compile(r"^##\s+\S+", re.MULTILINE)
# 识别代码块是否是「真正的简历 markdown」而非其他内容（如代码/JSON）。
# 放宽判断：很多 LLM 生成的简历首行是纯名字（无 # 标题），但有小节标题、
# 加粗、列表或分隔线等 markdown 结构。只要够长且含这些痕迹就认为是简历。
_MD_SIGNATURE_RE = re.compile(
    r"(^#{1,3}\s+\S)"           # 任意层级标题
    r"|(\*\*[^*]+\*\*)"          # 加粗 **xxx**
    r"|(^[-*]\s+\S)"             # 无序列表
    r"|(^---\s*$)",              # 分隔线
    re.MULTILINE,
)


def _extract_md_block(text: str):
    """
    从分析结果抽 ```md 代码块作为优化后的简历。返回 (md, source)。

    启发式评分替代原先的"取最长"：
      - 长度分：capped len / 100
      - 简历关键词分：包含"工作经历"/"教育背景"/"项目经验"/"技能"等核心小节 +5/项
      - 标题/列表/加粗结构 +1/项
    取得分最高的代码块；都不过关返回 None 走 fallback。
    """
    if not text:
        return None, "none"
    matches = _CODE_BLOCK_RE.findall(text)
    if not matches:
        return None, "none"

    # 简历常见中文小节标题；命中一个 +5 分
    resume_section_keywords = (
        "工作经历", "教育背景", "项目经验", "项目经历",
        "技能", "个人信息", "联系方式", "工作业绩",
        "教育经历", "实习经历", "工作项目", "工作项目经验",
    )

    def _score(candidate: str) -> int:
        score = 0
        score += min(len(candidate) // 100, 50)  # 长度分封顶 50
        for kw in resume_section_keywords:
            if kw in candidate:
                score += 5
        # markdown 结构信号
        score += len(_HEADING_RE.findall(candidate))
        score += len(_SECTION_RE.findall(candidate))
        return score

    best = max(matches, key=_score).strip()
    if _score(best) >= 5 and len(best) > 150:
        return best, "extracted"
    return None, "none"


# 用 _ALL_HEADING_RE 统计小节数（覆盖 1-3 级标题，避免漏计 ### 级）
_ALL_HEADING_RE = re.compile(r"^#{1,3}\s+\S+", re.MULTILINE)


def _count_sections(md: str) -> int:
    """统计 markdown 中的标题数量（1-3 级），用于返回 sections_detected。"""
    if not md:
        return 0
    return len(_ALL_HEADING_RE.findall(md))


# a4cv 能识别的简历小节标题关键词（与 a4cv looksLikeSectionTitle 对齐）。
# LLM 常把小节标题写成加粗 **工作经历** 而非 ## 工作经历，这里统一转成 ##，
# 让 a4cv 的 normalizeImportedMarkdown 能正确识别结构。
_A4CV_SECTION_KEYWORDS = (
    "自我评价|个人简介|职业概况|个人优势|工作经历|工作经验|项目经历|项目经验|"
    "实习经历|教育经历|教育背景|技能|技能特长|专业技能|证书|证书与荣誉|荣誉奖项|"
    "关键成果|作品集|发表论文|论文发表|社团经历|培训经历"
)
# 匹配独立的加粗小节标题行：**工作经历** 或 **工作经历**
_BOLD_SECTION_RE = re.compile(
    r"^[ \t]*\*{2}\s*(" + _A4CV_SECTION_KEYWORDS + r")\s*[:：]?\*{2}[ \t]*$",
    re.MULTILINE,
)


def _normalize_md_for_a4cv(md: str) -> str:
    """
    把 LLM 生成的简历 markdown 标准化，让 a4cv 编辑器能正确识别结构：
    1. 加粗小节标题转 ## 标题：**工作经历** → ## 工作经历
    2. 首行若是纯名字（无 #），补成 # 姓名（a4cv 靠 # 识别姓名栏）

    a4cv 的 normalizeImportedMarkdown：只要 markdown 含任何 # 标题就走
    normalizeHeadingMarkdown 直接返回，不会自动补 # 姓名。而 LLM 常把姓名
    写成纯文本首行，所以必须在这里补上。
    """
    if not md:
        return md

    def _repl(m):
        return f"## {m.group(1)}"

    md = _BOLD_SECTION_RE.sub(_repl, md)

    # 首行补 # 姓名：若首行不是标题、不是空行、也不是联系方式行，视为姓名
    lines = md.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue  # 跳过前导空行
        if stripped.startswith("#"):
            break  # 首个非空行已是标题，无需补
        # 简易判断：联系方式行（含 @ 或多个数字）不当作姓名
        if "@" in stripped or re.search(r"\d{4,}", stripped):
            break
        lines[i] = f"# {stripped}"
        break

    return "\n".join(lines)


def _build_fallback_markdown(processed: dict) -> str:
    """从结构化简历拼 a4cv 兼容的最小 markdown。"""
    pd = processed.get("personal_data") or {}
    name = pd.get("firstName") or pd.get("name") or "你的姓名"
    title = pd.get("title") or pd.get("position") or ""

    contact_bits = []
    for key in ("email", "phone"):
        v = pd.get(key)
        if v:
            contact_bits.append(str(v))
    loc = pd.get("location")
    if isinstance(loc, dict):
        city = loc.get("city")
        if city:
            contact_bits.append(str(city))
    for key in ("linkedin", "portfolio"):
        v = pd.get(key)
        if v:
            contact_bits.append(str(v))

    out = [f"# {name}"]
    if title:
        out.append(f"## {title}")
    if contact_bits:
        out += ["", "> " + " · ".join(contact_bits)]

    experiences = processed.get("experiences") or []
    if experiences:
        out += ["", "## 工作经历"]
        for e in experiences:
            t = e.get("job_title") or e.get("jobTitle") or "职位"
            c = e.get("company") or ""
            sd = e.get("start_date") or e.get("startDate") or ""
            ed = e.get("end_date") or e.get("endDate") or ""
            meta = " · ".join(x for x in (c, f"{sd} - {ed}" if sd else "") if x)
            out.append(f"### {t}" + (f" | {meta}" if meta else ""))
            for b in e.get("description") or []:
                if b:
                    out.append(f"- {b}")

    projects = processed.get("projects") or []
    if projects:
        out += ["", "## 项目经历"]
        for p in projects:
            t = p.get("project_name") or p.get("projectName") or "项目"
            desc = p.get("description") or ""
            out.append(f"### {t}")
            if desc:
                out.append(f"- {desc}")

    education = processed.get("education") or []
    if education:
        out += ["", "## 教育背景"]
        for ed in education:
            school = ed.get("institution") or "学校"
            degree = ed.get("degree") or ""
            out.append(f"### {school}" + (f" | {degree}" if degree else ""))

    skills = processed.get("skills") or []
    if skills:
        out += ["", "## 技能标签"]
        names = []
        for s in skills:
            if isinstance(s, dict):
                names.append(s.get("skill_name") or s.get("skillName") or "")
            else:
                names.append(str(s))
        out.append(" · ".join(filter(None, names)))

    achievements = processed.get("achievements") or []
    if achievements:
        out += ["", "## 证书与荣誉"]
        for a in achievements:
            out.append(f"- {a}")

    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    # 仅本地直接 python app.py 时用；生产请用 gunicorn app:app
    app.run(host="127.0.0.1", port=config.BACKEND_PORT, debug=(config.ENV != "production"))
