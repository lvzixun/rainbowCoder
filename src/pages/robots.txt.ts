import { withBase, siteUrl } from '../lib/site.mjs';
export function GET() {
  return new Response(`User-agent: *\nAllow: /\nSitemap: ${new URL(withBase('/sitemap-index.xml'), siteUrl).href}\n`, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}
