// Rasterises docs/assets/*.svg to 2x PNGs for the README.
// Usage: node docs/assets/render_png.cjs   (requires the `playwright` package with Chromium)
const path = require('path');
const fs = require('fs');
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')); }

const DIR = __dirname;
const NAMES = ['hero', 'badges', 'agents', 'evidence-hunter', 'readiness', 'architecture'];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 2, viewport: { width: 900, height: 900 } });
  for (const name of NAMES) {
    const svg = path.join(DIR, `${name}.svg`);
    const html = path.join(DIR, `.render-${name}.html`);
    fs.writeFileSync(html, `<html><body style="margin:0;background:transparent"><img id="i" src="${name}.svg" style="display:block;width:900px"></body></html>`);
    await page.goto('file://' + html);
    await page.waitForTimeout(2600); // let entry animations finish
    await (await page.$('#i')).screenshot({ path: path.join(DIR, `${name}.png`), omitBackground: true, animations: 'allow', timeout: 15000 });
    fs.unlinkSync(html);
    console.log(`${name}.png`, Math.round(fs.statSync(path.join(DIR, `${name}.png`)).size / 1024), 'KB');
  }
  await browser.close();
})();
