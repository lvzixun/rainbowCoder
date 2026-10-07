export const siteUrl = new URL(process.env.SITE_URL || 'https://lvzixun.github.io/rainbowCoder/').href;
export const siteOrigin = new URL(siteUrl).origin;
export const siteBase = new URL(siteUrl).pathname.replace(/\/$/, '');
export function withBase(value) {
  if (!value.startsWith('/') || value.startsWith('//') || !siteBase) return value;
  if (value === siteBase || value.startsWith(siteBase + '/')) return value;
  return siteBase + value;
}
export function stripBase(value) {
  if (siteBase && (value === siteBase || value.startsWith(siteBase + '/'))) return value.slice(siteBase.length) || '/';
  return value;
}
export const site = {
  title: 'rainbowCoder',
  author: 'zixun',
  description: '关于 Lua、编译器与游戏服务端的技术笔记。',
  github: 'https://github.com/lvzixun',
  repository: 'https://github.com/lvzixun/rainbowCoder',
  email: 'lvzixun@gmail.com',
};
