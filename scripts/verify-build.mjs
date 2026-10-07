import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { siteUrl } from '../src/lib/site.mjs';

const root = path.resolve('dist');
const files = readdirSync(root, { recursive: true }).filter(file => file.endsWith('.html') && statSync(path.join(root, file)).isFile());
const articles = readdirSync('post').filter(file => file.endsWith('.md') && !/^draft:\s*true\s*$/m.test(readFileSync(`post/${file}`, 'utf8')));
assert(articles.length > 0, 'No published articles');
for (const file of articles) assert(statSync(path.join(root, file.replace(/\.md$/, '.html'))).isFile(), `Missing article file ${file}`);
const ids = new Map();
for (const file of files) {
  const html = readFileSync(path.join(root, file), 'utf8');
  ids.set(file, new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1])));
}
let checkedLinks = 0;
for (const file of files) {
  const html = readFileSync(path.join(root, file), 'utf8');
  assert.equal((html.match(/<h1\b/g) || []).length, 1, `${file}: expected one H1`);
  assert(html.includes('lang="zh-CN"'), `${file}: missing language`);
  assert(html.includes('<meta name="description"'), `${file}: missing description`);
  assert(!html.includes('rainbowcoder.invalid'), `${file}: placeholder origin`);
  assert(!/<a\b[^>]*href="https?:\/\/(?:www\.)?rainbowcoder\.com/i.test(html), `${file}: stale internal domain`);
  const pageUrl = new URL(file === 'index.html' ? '/' : '/' + file.replace(/\/index\.html$/, '/'), siteUrl);
  for (const match of html.matchAll(/<(?:a|link|img|script)\b[^>]*?\b(?:href|src)="([^"]+)"/g)) {
    const reference = match[1].replaceAll('&amp;', '&');
    if (/^(mailto:|tel:|data:|javascript:)/.test(reference)) continue;
    const url = new URL(reference, pageUrl);
    if (url.origin !== new URL(siteUrl).origin) continue;
    const decoded = decodeURIComponent(url.pathname);
    let target = path.join(root, decoded);
    if (existsSync(target) && statSync(target).isDirectory()) target = path.join(target, 'index.html');
    assert(existsSync(target), `${file}: missing local target ${reference}`);
    if (url.hash && target.endsWith('.html')) {
      assert(ids.get(path.relative(root, target))?.has(decodeURIComponent(url.hash.slice(1))), `${file}: broken fragment ${reference}`);
    }
    checkedLinks++;
  }
}
const feed = readFileSync(path.join(root, 'rainbowcoder_rss.xml'), 'utf8');
assert.equal((feed.match(/<item>/g) || []).length, articles.length, 'RSS article count mismatch');
assert(feed.includes(new URL(siteUrl).origin), 'RSS origin mismatch');
assert(existsSync(path.join(root, 'sitemap-index.xml')), 'Missing sitemap');
const sitemap = readFileSync(path.join(root, 'sitemap-0.xml'), 'utf8');
for (const article of articles) assert(sitemap.includes(`/${article.replace(/\.md$/, '.html')}</loc>`), `Sitemap missing canonical article ${article}`);
assert(existsSync(path.join(root, '404.html')), 'Missing 404 page');
assert(readFileSync(path.join(root, 'robots.txt'), 'utf8').includes('/sitemap-index.xml'), 'Missing robots sitemap');
console.log(`Verified ${articles.length} articles, ${files.length} HTML pages, ${checkedLinks} internal references, RSS and sitemap.`);
