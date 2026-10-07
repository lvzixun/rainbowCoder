# rainbowCoder

zixun 的个人技术博客。Astro 构建，文章保存在 `post/`，发布为静态网站。

站点：<https://rainbowcoder-zixun.lvzixun.chatgpt.site>

## 本地开发

需要 Node.js 22.12+。

```sh
npm ci
npm run dev
npm run check      # 类型与模板检查
npm run build      # 构建到 dist/
npm run verify     # 检查文章、内部链接和 RSS
npm run preview    # 预览构建产物
```

## 写文章

在 `post/` 新建 Markdown，文件名即文章地址，如 `lua.md` 对应 `/lua.html`。

```markdown
---
title: 一篇新的文章
date: 2026-10-07
description: 用一句话介绍文章。
tags: [Lua]
---

正文从这里开始。
```

`updated` 可选，仅在实质更新正文时填写。`draft: true` 的文章不会出现在生产站点。不要更改已发布文件名，以免影响外链和评论关联。

图片放在 `public/images/`，通过 `/images/example.png` 引用。支持 GFM 表格、C / Lua / diff 代码高亮、文章目录和 RSS。

## 结构

- `post/`：Markdown 文章及元数据。
- `src/pages/`：首页、归档、文章、关于、RSS。
- `src/components/`、`src/layouts/`：共享界面。
- `src/styles/`：主题和文章排版。
- `src/lib/`：内容读取与公共配置。
- `public/`：静态资源。
- `scripts/`：迁移与构建产物检查。
- `.openai/hosting.json`：Sites 托管配置。

## 发布

当前使用 Sites 托管。更新源码后，可让支持 Sites 的助手检查、构建并重新发布；也可将 `dist/` 发布到其他静态托管平台。`SITE_URL` 环境变量可覆盖生产站点地址。

GitHub Actions 在提交和 Pull Request 中执行检查、构建与链接验证。GitHub 源码推送不会自动更新 Sites；部署由 Sites 发布流程完成。

## 历史迁移

保留原 Git 历史和 13 篇旧文。旧 `.html` 地址及 `/rainbowcoder_rss.xml` 继续提供。原域名已停用，正文内指向原站的链接改为站内链接。

日期取完整 Git 历史中每个文件最早的提交，更新时间取迁移前最后一次提交，仅在不同日期时显示。这些日期反映可恢复的记录。正文保留原有内容，修正代码块语言标记和排版兼容问题。

旧 Python 2 / Lua 构建和 SSH 发布脚本已移除，可从 Git 历史查看。

Lua 5.4 GC 插图和旧新浪插件演示 GIF 均已迁到本地，阅读时无需访问原图床。
