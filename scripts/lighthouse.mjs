import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const [modules, chromePath, url, output] = process.argv.slice(2);
const require = createRequire(path.join(modules, '__qa__.cjs'));
const {default: lighthouse} = await import(pathToFileURL(require.resolve('lighthouse')).href);
const launcher = await import(pathToFileURL(require.resolve('chrome-launcher')).href);
const chrome = await launcher.launch({chromePath, chromeFlags: ['--headless', '--no-sandbox', '--disable-gpu']});
try {
  const result = await lighthouse(url, {port: chrome.port, output: ['json','html'], onlyCategories: ['performance','accessibility','best-practices','seo']});
  if (result.lhr.runtimeError) throw new Error(result.lhr.runtimeError.message);
  const scores = Object.fromEntries(Object.entries(result.lhr.categories).map(([key, value]) => [key, Math.round(value.score * 100)]));
  await fs.writeFile(output, JSON.stringify({evidence_label: 'REAL VERIFIED', lighthouse_version: result.lhr.lighthouseVersion, scores, report: result.lhr}, null, 2));
  await fs.writeFile(output.replace(/\.json$/, '.html'), result.report[1]);
  process.stdout.write(JSON.stringify(scores));
} finally { await chrome.kill(); }
