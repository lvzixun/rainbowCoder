import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { posts } from '../lib/posts';
import { site } from '../lib/site.mjs';
export async function GET(context: APIContext) {
  return rss({
    title: 'rainbowCoder · zixun 的技术笔记',
    description: site.description,
    site: context.site!,
    items: await Promise.all(posts.map(async post => ({
      title: post.title,
      description: post.description,
      content: (await post.html).replace(/(href|src)="(\/[^\"]*)"/g, (_, attribute, url) => `${attribute}="${new URL(url, context.site).href}"`),
      pubDate: new Date(`${post.date}T00:00:00+08:00`),
      link: post.href,
      categories: post.tags,
    }))),
    customData: '<language>zh-cn</language>',
  });
}
