import type { MarkdownInstance } from 'astro';

export interface Frontmatter {
  title: string;
  date: string | Date;
  updated?: string | Date;
  description: string;
  tags: string[];
  draft?: boolean;
}

const modules = import.meta.glob<MarkdownInstance<Frontmatter>>('../../post/*.md', { eager: true });
function dateString(value: string | Date) {
  return value instanceof Date ? value.toISOString().slice(0, 10) : String(value).slice(0, 10);
}
export const posts = Object.entries(modules)
  .filter(([, entry]) => !entry.frontmatter.draft)
  .map(([path, entry]) => {
    const slug = path.split('/').pop()!.replace(/\.md$/, '');
    const data = entry.frontmatter;
    if (!data.title || !data.description || !data.date || !Array.isArray(data.tags)) {
      throw new Error(`文章 ${slug} 缺少 title/date/description/tags 元数据`);
    }
    const date = dateString(data.date);
    const updated = data.updated ? dateString(data.updated) : undefined;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date))) throw new Error(`文章 ${slug} 的日期无效`);
    const text = entry.rawContent().replace(/(?:```|~~~)[\s\S]*?(?:```|~~~)/g, '').replace(/<[^>]*>/g, '');
    const chinese = (text.match(/[\u4e00-\u9fff]/g) || []).length;
    const words = (text.replace(/[\u4e00-\u9fff]/g, ' ').match(/\S+/g) || []).length;
    const minutes = Math.max(1, Math.ceil(chinese / 350 + words / 220));
    return { ...data, slug, href: `/${slug}.html`, date, updated, minutes, Content: entry.Content, headings: entry.getHeadings(), html: entry.compiledContent() };
  })
  .sort((a, b) => b.date.localeCompare(a.date) || a.slug.localeCompare(b.slug));
export const tags = [...new Set(posts.flatMap(post => post.tags))];
export const years = [...new Set(posts.map(post => post.date.slice(0, 4)))];
export const displayDate = (date: string) => date.replaceAll('-', '.');
