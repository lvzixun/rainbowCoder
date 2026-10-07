import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { siteUrl } from './src/lib/site.mjs';

export default defineConfig({
  site: siteUrl,
  output: 'static',
  build: { format: 'preserve' },
  integrations: [sitemap({
    serialize(item) {
      const url = new URL(item.url);
      if (url.pathname === '/about' || url.pathname === '/archive') url.pathname += '/';
      else if (url.pathname !== '/' && !url.pathname.endsWith('.html')) url.pathname = url.pathname.replace(/\/$/, '') + '.html';
      return { ...item, url: url.href };
    },
  })],
  markdown: {
    syntaxHighlight: 'shiki',
    shikiConfig: {
      themes: { light: 'github-light', dark: 'github-dark' },
      defaultColor: false,
      wrap: false,
    },
  },
});
