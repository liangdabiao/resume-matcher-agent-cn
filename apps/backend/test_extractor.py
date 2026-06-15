"""Quick sanity test for the markdown_extractor module."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.markdown_extractor import (
    extract_improved_markdown,
    build_fallback_markdown,
    count_sections,
)


SAMPLE_WITH_CODE_BLOCK = """# HR 反馈报告

## 第一印象

不错的简历。

```md
# 张三
## 高级前端工程师
> 北京 · zhangsan@example.com · 13800138000

## 工作经历
### 字节跳动 · 高级前端 | 2022-2024
- 负责抖音商家端
- 提升 30% 性能

## 项目经历
### 抖音商城 | 2023
- 重构结算流程

## 教育背景
### 清华 · 计算机 | 2018-2022

## 技能标签
React · TypeScript · Webpack
```

## 最终评语

加油。
"""

SAMPLE_WITHOUT_CODE_BLOCK = """# HR 反馈报告

## 第一印象

不够好。

## 最终评语

需要改进。
"""

# ---- Test extract_improved_markdown ----
md, src = extract_improved_markdown(SAMPLE_WITH_CODE_BLOCK)
assert src == "extracted", f"expected extracted, got {src}"
assert md is not None
assert "# 张三" in md, f"missing 张三 in extracted: {md!r}"
assert "## 工作经历" in md
assert "## 技能标签" in md
assert "```" not in md, "code fences should be stripped"
print(f"[OK] extract with code block: source={src}, len={len(md)}, sections={count_sections(md)}")

md2, src2 = extract_improved_markdown(SAMPLE_WITHOUT_CODE_BLOCK)
assert md2 is None
assert src2 == "none"
print("[OK] extract without code block returns None")

# ---- Test build_fallback_markdown ----
class PR: pass

pr = PR()
pr.personal_data = json.dumps({
    "name": "李四",
    "title": "产品经理",
    "email": "li@example.com",
    "phone": "13800138000",
    "location": "深圳"
}, ensure_ascii=False)
pr.experiences = json.dumps({"experiences": [
    {"title": "产品经理", "company": "腾讯", "period": "2020-2024", "description": ["负责微信视频号", "DAU 突破1亿"]}
]}, ensure_ascii=False)
pr.projects = json.dumps({"projects": [
    {"title": "视频号改版", "role": "主PM", "period": "2023", "description": ["改版方案设计", "数据提升 50%"]}
]}, ensure_ascii=False)
pr.education = json.dumps({"education": [
    {"school": "北大", "degree": "本科", "period": "2016-2020"}
]}, ensure_ascii=False)
pr.skills = json.dumps({"skills": [
    {"name": "产品设计"}, {"name": "用户研究"}, "SQL"
]}, ensure_ascii=False)
pr.achievements = json.dumps({"achievements": [
    {"title": "腾讯优秀员工"}
]}, ensure_ascii=False)
pr.research_work = json.dumps({"research_work": []}, ensure_ascii=False)

fallback = build_fallback_markdown(pr)
assert "# 李四" in fallback
assert "## 产品经理" in fallback
assert "## 工作经历" in fallback
assert "## 项目经历" in fallback
assert "## 教育背景" in fallback
assert "## 技能标签" in fallback
assert "## 证书与荣誉" in fallback
print(f"[OK] fallback markdown: sections={count_sections(fallback)}")
print("---FALLBACK START---")
print(fallback)
print("---FALLBACK END---")

# Empty ProcessedResume should still produce a valid skeleton
pr2 = PR()
pr2.personal_data = json.dumps({"name": "王五"}, ensure_ascii=False)
pr2.experiences = None
pr2.projects = None
pr2.education = None
pr2.skills = None
pr2.achievements = None
pr2.research_work = None
fb2 = build_fallback_markdown(pr2)
assert "# 王五" in fb2
print("[OK] minimal fallback (only name) works")

print("\nALL TESTS PASSED")
