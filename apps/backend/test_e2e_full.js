// Full pipeline test: simulate the EXACT same JS logic the dashboard button
// runs, then verify a4cv opens and renders the resume.

const puppeteer = require('puppeteer-core');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const API_URL = 'http://127.0.0.1:8000/api/v1/resumes/improved-markdown';
const A4CV_URL = 'http://localhost:3001/a4cv/index.html?pickup=session';

const SAMPLE_ANALYSIS = `# HR 反馈

## 摘要

不错的简历。

\`\`\`md
# 李四
## 资深产品经理
> 上海 · li@example.com · 13900139000

## 工作经历
### 阿里巴巴 · 高级产品经理 | 2019-2024
- 负责淘宝直播
- DAU 突破 5000 万
- 推动 GMV 增长 80%

## 项目经历
### 直播带货改版 | 2022
- 主 PM
- 转化率提升 35%

## 教育背景
### 浙江大学 · 工商管理 | 2015-2019

## 技能标签
用户研究 · 数据分析 · SQL · Axure · Figma

## 证书与荣誉
- 阿里 P7 优秀员工
- MBA 案例大赛一等奖
\`\`\`

## 最终评语
建议丰富一些早期项目。
`;

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 900 });

    // Land on the dashboard origin first so subsequent fetches share the
    // same origin (and same sessionStorage store) that a real user would.
    console.log('Bootstrapping on dashboard origin: http://localhost:3001/dashboard');
    await page.goto('http://localhost:3001/dashboard', { waitUntil: 'domcontentloaded', timeout: 30000 });

    // Mirror what dashboard's handleOpenInEditor does, on the dashboard origin
    // (so sessionStorage is the same store that /a4cv reads from).
    console.log('Step 1: calling /improved-markdown from a same-origin page...');
    const result = await page.evaluate(async ({ apiUrl, analysisResult, resumeId, jobId }) => {
      try {
        const res = await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ resume_id: resumeId, job_id: jobId, analysis_result: analysisResult }),
        });
        if (!res.ok) {
          return { ok: false, status: res.status, body: await res.text() };
        }
        const json = await res.json();
        const md = json?.data?.markdown;
        if (!md) return { ok: false, reason: 'no markdown in response' };
        // Stash exactly like the button does
        sessionStorage.setItem('pendingResumeMD', md);
        return {
          ok: true,
          source: json.data.source,
          sections: json.data.sections_detected,
          stash_len: sessionStorage.getItem('pendingResumeMD').length,
        };
      } catch (e) {
        return { ok: false, reason: String(e) };
      }
    }, { apiUrl: API_URL, analysisResult: SAMPLE_ANALYSIS, resumeId: 'mock-r-1', jobId: 'mock-j-1' });

    console.log('  result:', result);
    if (!result.ok) {
      throw new Error('Step 1 failed: ' + JSON.stringify(result));
    }
    if (result.source !== 'extracted') {
      throw new Error('expected source=extracted, got ' + result.source);
    }
    if (result.sections < 4) {
      throw new Error('expected sections>=4, got ' + result.sections);
    }
    console.log('  PASS: backend returned markdown and it was stashed in sessionStorage');

    // Now navigate to a4cv with the same session storage (same browser context)
    console.log('\nStep 2: navigating to a4cv with the same session storage...');
    const opened = await page.goto(A4CV_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    console.log('  HTTP', opened.status());

    // Poll for the name to appear
    let appeared = false;
    for (let i = 0; i < 30; i++) {
      const has = await page.evaluate(() => document.body.innerText.includes('李四'));
      if (has) { appeared = true; break; }
      await new Promise((r) => setTimeout(r, 400));
    }
    if (!appeared) {
      const body = (await page.evaluate(() => document.body.innerText)).slice(0, 800);
      console.log('--- body sample ---\n' + body);
      throw new Error('name "李四" did not appear in a4cv');
    }
    console.log('  PASS: a4cv rendered 李四 from the sessionStorage value');

    // Verify the value was consumed
    const remaining = await page.evaluate(() => sessionStorage.getItem('pendingResumeMD'));
    if (remaining) {
      throw new Error('sessionStorage key not consumed, len=' + remaining.length);
    }
    console.log('  PASS: sessionStorage key was consumed (one-shot)');

    // Capture a final screenshot
    await page.setViewport({ width: 1400, height: 900 });
    await page.screenshot({ path: 'a4cv-full-pipeline.png', fullPage: false });
    console.log('  Screenshot: a4cv-full-pipeline.png');

    console.log('\nEND-TO-END PIPELINE VERIFIED');
  } catch (e) {
    console.error('FAIL:', e.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
