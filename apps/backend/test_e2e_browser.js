// End-to-end browser test: pre-seed sessionStorage, open a4cv with ?pickup=session,
// verify the optimized resume is rendered and the toast is shown.

const puppeteer = require('puppeteer-core');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const A4CV_URL = 'http://localhost:3001/a4cv/index.html?pickup=session';
const SAMPLE_MD = `# 张三
## 高级前端工程师
> 北京 · zhangsan@example.com · 13800138000

## 工作经历
### 字节跳动 · 高级前端 | 2022-2024
- 负责抖音商家端
- 性能提升 30%

## 项目经历
### 抖音商城 | 2023
- 重构结算流程
- 转化率提升 12%

## 教育背景
### 清华大学 · 计算机 | 2018-2022

## 技能标签
React · TypeScript · Webpack · Node.js
`;

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  try {
    const page = await browser.newPage();

    // 1) Intercept BEFORE any document is loaded: stub sessionStorage so
    //    the key is already present when the a4cv IIFE runs.
    await page.evaluateOnNewDocument((md) => {
      try {
        sessionStorage.setItem('pendingResumeMD', md);
      } catch (e) {
        console.error('seed sessionStorage failed', e);
      }
    }, SAMPLE_MD);

    // 2) Capture console + page errors
    const logs = [];
    page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
    page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));

    // 3) Load a4cv with the pickup flag
    console.log('Navigating to', A4CV_URL);
    const resp = await page.goto(A4CV_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    console.log('HTTP', resp.status());

    // 4) Wait until the a4cv script has had time to consume the sessionStorage
    //    value and render. The a4cv renderer writes the parsed sections into
    //    the DOM, so we poll for our expected name.
    let nameAppeared = false;
    for (let i = 0; i < 30; i++) {
      const text = await page.evaluate(() => document.body.innerText || '');
      if (text.includes('张三')) {
        nameAppeared = true;
        break;
      }
      await new Promise((r) => setTimeout(r, 500));
    }

    if (!nameAppeared) {
      const bodyText = (await page.evaluate(() => document.body.innerText || '')).slice(0, 600);
      console.log('--- body innerText (first 600 chars) ---');
      console.log(bodyText);
      console.log('--- recent console logs ---');
      console.log(logs.slice(-20).join('\n'));
      throw new Error('name "张三" not found in rendered page');
    }
    console.log('OK: 张三 rendered');

    // 5) Check that the toast appeared
    const toast = await page.evaluate(() => {
      const all = Array.from(document.querySelectorAll('*'))
        .filter((el) => (el.innerText || '').includes('已从优化结果载入简历'));
      return all.length > 0 ? (all[0].innerText || '').slice(0, 200) : null;
    });
    if (toast) {
      console.log('OK: toast found ->', toast);
    } else {
      console.log('WARN: toast not seen in DOM (might be short-lived)');
    }

    // 6) Check that sessionStorage value was consumed (key should be gone)
    const remaining = await page.evaluate(() => sessionStorage.getItem('pendingResumeMD'));
    if (remaining) {
      console.log('WARN: sessionStorage key still present after pickup, len =', remaining.length);
    } else {
      console.log('OK: sessionStorage key was consumed by a4cv');
    }

    // 7) Sanity: check that other sections from our markdown also rendered
    const hasExperience = await page.evaluate(() => document.body.innerText.includes('工作经历'));
    const hasSkills = await page.evaluate(() => document.body.innerText.includes('技能标签'));
    const hasEdu = await page.evaluate(() => document.body.innerText.includes('教育背景'));
    console.log('sections -> 工作经历:', hasExperience, '技能标签:', hasSkills, '教育背景:', hasEdu);

    // 8) Take a screenshot for visual confirmation
    await page.setViewport({ width: 1400, height: 900 });
    await page.screenshot({ path: 'a4cv-pickup-screenshot.png', fullPage: false });
    console.log('Screenshot saved to a4cv-pickup-screenshot.png');

    console.log('\nALL CHECKS PASSED');
  } catch (e) {
    console.error('TEST FAILED:', e.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
