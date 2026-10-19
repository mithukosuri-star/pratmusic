/* Run against python3 server.py 8000; requires puppeteer-core and @sparticuz/chromium. */
const assert = require('node:assert/strict');
(async () => {
  const puppeteer = require('puppeteer-core');
  const mod = require('@sparticuz/chromium');
  const chromium = mod.default || mod;
  const path = require('node:path');
  await mod.inflate(path.join(path.dirname(require.resolve('@sparticuz/chromium')), '..', 'bin', 'al2023.tar.br'));
  mod.setupLambdaEnvironment('/tmp/al2023/lib');
  const browser = await puppeteer.launch({ executablePath: await chromium.executablePath(), args: chromium.args, headless: true });
  try {
    for (const [width, height] of [[320,568],[390,844],[768,1024],[1366,768],[1440,900],[844,390]]) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.setViewport({ width, height });
      await page.goto('http://127.0.0.1:8000/#library', {waitUntil:'networkidle0'});
      await page.waitForSelector('.card');
      // Mouse wheel / touchpad uses the document, not a clipped flex child.
      await page.mouse.move(width - 24, Math.floor(height / 2));
      await page.mouse.wheel({deltaY:650});
      await new Promise(r => setTimeout(r, 250));
      assert.ok(await page.evaluate(() => scrollY > 0), `${width}: wheel scroll`);
      if (width < 600) {
        await page.evaluate(() => window.scrollTo(0, 0));
        const session = await page.createCDPSession();
        await session.send('Emulation.setTouchEmulationEnabled', {enabled:true});
        const x = Math.round(width / 2), y = Math.round(height * .65);
        await session.send('Input.dispatchTouchEvent', {type:'touchStart', touchPoints:[{x,y}]});
        for (let step=1; step<=10; step++) {
          await session.send('Input.dispatchTouchEvent', {type:'touchMove', touchPoints:[{x,y:y-step*20}]});
          await new Promise(r=>setTimeout(r,20));
        }
        await session.send('Input.dispatchTouchEvent', {type:'touchEnd', touchPoints:[]});
        await new Promise(r=>setTimeout(r,150));
        assert.ok(await page.evaluate(() => scrollY > 0), `${width}: touch scroll`);
        await session.detach();
      }
      const result = await page.evaluate(() => {
        window.scrollTo(0, document.documentElement.scrollHeight);
        const cards = document.querySelectorAll('.card');
        return {
          overflow: document.documentElement.scrollWidth > innerWidth,
          lastBottom: cards[cards.length-1].getBoundingClientRect().bottom,
          playerTop: document.querySelector('#player').getBoundingClientRect().top,
          navLabels: [...document.querySelectorAll('.nav-btn span')].every(e => getComputedStyle(e).display !== 'none')
        };
      });
      assert.equal(result.overflow, false, `${width}: horizontal overflow`);
      assert.ok(result.lastBottom <= result.playerTop, `${width}: final track obscured: ${JSON.stringify(result)}`);
      assert.ok(result.navLabels, `${width}: navigation labels visible`);
      assert.deepEqual(errors, []);
      console.log(`PASS ${width}x${height}: wheel scrolling, no overflow, final track clear, navigation visible`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
