import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { satteri } from '@astrojs/markdown-satteri';
import { siteOrigin, siteBase, stripBase, withBase } from './src/lib/site.mjs';
import { markdownLinks } from './src/lib/markdown-links.mjs';

export default defineConfig({
  site: siteOrigin,
  base: siteBase || '/',
  output: 'static',
  build: { format: 'preserve' },
  integrations: [sitemap({
    serialize(item) {
      const url = new URL(item.url);
      let pathname = stripBase(url.pathname);
      if (pathname === '/about' || pathname === '/archive') pathname += '/';
      else if (pathname !== '/' && !pathname.endsWith('.html')) pathname = pathname.replace(/\/$/, '') + '.html';
      url.pathname = withBase(pathname);
      return { ...item, url: url.href };
    },
  })],
  markdown: {
    processor: satteri({ hastPlugins: [markdownLinks] }),
    syntaxHighlight: 'shiki',
    shikiConfig: {
      themes: { light: 'github-light', dark: 'tokyo-night' },
      defaultColor: false,
      wrap: false,
    },
  },
});
