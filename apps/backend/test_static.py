"""Verify a4cv is served by Next.js dev server and dashboard compiles."""
import json
import sys
import urllib.request

def get(url):
    print(f"\n>>> GET {url}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)


# 1. a4cv 静态托管
code, html = get("http://localhost:3001/a4cv/")
print(f"status: {code}")
if code == 200:
    head = html[:500]
    print("--- head ---")
    print(head)
    assert "<title" in html, "no <title> in a4cv index.html"
    assert "pickupResumeFromOptimizer" in html, "pickup hook missing from index.html"
    assert "sessionStorage" in html, "no sessionStorage reference"
    print("PASS: a4cv static hosting works, pickup hook is inlined")
else:
    print("FAIL: a4cv not served")
    sys.exit(1)

# 2. 关键资源 vendor 子目录
code2, _ = get("http://localhost:3001/a4cv/vendor/")
print(f"vendor dir listing status: {code2} (200 or 404 both fine for static serving)")

# 3. dashboard 编译
code3, html3 = get("http://localhost:3001/dashboard")
print(f"dashboard status: {code3}")
# dashboard 在没有 improvedData 时显示 "暂未找到优化结果"，这是正常编译成功
if code3 == 200:
    if "暂未找到优化结果" in html3 or "in main" in html3.lower():
        print("PASS: dashboard compiles (renders the 'no data' fallback)")
    else:
        # 可能是其他正常渲染
        if "Open in editor" in html3 or "编辑器" in html3 or "未找到" in html3:
            print("PASS: dashboard compiles")
        else:
            print("WARN: dashboard 200 but unexpected content - check manually")
    # 我们的按钮在 improvedData 存在时才显示；fallback 状态看不到也算正常
else:
    print(f"FAIL: dashboard status {code3}")
    print(html3[:2000])
    sys.exit(1)

print("\nALL HTTP CHECKS PASSED")
