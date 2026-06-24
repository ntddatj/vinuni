const { chromium } = require('/tmp/pw-verify/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1680, height: 900 }, deviceScaleFactor: 2 });
  await page.goto('file://' + process.cwd() + '/layout-tabs-restructure.html');
  await page.screenshot({ path: 'layout-tabs-restructure.png', fullPage: true });
  await browser.close();
  console.log('done');
})();
