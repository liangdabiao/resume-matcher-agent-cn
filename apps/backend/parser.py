"""
文档解析：从 PDF / DOCX 提取纯文本。
逻辑照搬自旧版 resume_service.py，仅去掉类封装。
"""
import io
import zipfile
import xml.etree.ElementTree as ET

from pdfminer.high_level import extract_text

# DOCX 段落命名空间
_WML_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_pdf(file_bytes: bytes) -> str:
    """用 pdfminer 提取 PDF 文本。"""
    return extract_text(io.BytesIO(file_bytes))


def extract_docx(file_bytes: bytes) -> str:
    """手写 zip+xml 解析 DOCX（仅依赖标准库，不装 python-docx）。"""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx:
            document_xml = docx.read("word/document.xml")
    except KeyError as e:
        raise ValueError("Invalid DOCX file: missing word/document.xml") from e
    except zipfile.BadZipFile as e:
        raise ValueError("Invalid DOCX file") from e

    root = ET.fromstring(document_xml)
    paragraphs = []
    for paragraph in root.iter(f"{_WML_NS}p"):
        texts = [node.text for node in paragraph.iter(f"{_WML_NS}t") if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def extract_text_from_file(file_bytes: bytes, content_type: str) -> str:
    """
    根据 MIME 类型提取文本。

    content_type: application/pdf 或
                  application/vnd.openxmlformats-officedocument.wordprocessingml.document
    """
    if content_type == "application/pdf":
        text = extract_pdf(file_bytes)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_docx(file_bytes)
    else:
        raise ValueError("Unsupported file type")

    text = text.strip()
    if not text:
        raise ValueError("No text could be extracted from the uploaded file")
    return text
