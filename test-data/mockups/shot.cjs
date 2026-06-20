const { chromium } = require('/tmp/pw-verify/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
  await page.goto('file://' + process.cwd() + '/layout-chat-top.html');
  await page.screenshot({ path: 'layout-chat-top.png' });
  await browser.close();
  console.log('done');
})();
