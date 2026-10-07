# rainbowCoder

zixun 的个人技术博客。Astro 构建，文章保存在 `post/`，发布为静态网站。默认深色编辑器风格，支持浅色主题、搜索、主题筛选和代码复制。

站点：<https://lvzixun.github.io/rainbowCoder/>

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

在 `post/` 新建 Markdown，文件名即文章地址，如 `lua.md` 对应 `/rainbowCoder/lua.html`。

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
- `.github/workflows/pages.yml`：GitHub Pages 自动发布。

## 发布

正式站点使用免费的 GitHub Pages。仓库 Settings → Pages → Source 选择 **GitHub Actions**（已开通）。推送到 `master` 后，`Publish blog` 工作流自动执行检查、构建、链接验证并发布；Actions 页面可查看部署状态。Pull Request 和其他分支运行构建检查。

默认站点地址为 `https://lvzixun.github.io/rainbowCoder/`，站内链接、图片、RSS 与 sitemap 自动带上 `/rainbowCoder/`。写 Markdown 时继续使用 `/images/example.png` 等根路径，构建会补全站点前缀。修改托管地址时同步修改发布工作流的 `SITE_URL`；本地也可用该环境变量覆盖地址。

## 历史迁移

保留原 Git 历史和 13 篇旧文。旧 `.html` 地址及 `/rainbowcoder_rss.xml` 继续提供。原域名已停用，正文内指向原站的链接改为站内链接。

日期取完整 Git 历史中每个文件最早的提交，更新时间取迁移前最后一次提交，仅在不同日期时显示。这些日期反映可恢复的记录。正文保留原有内容，修正代码块语言标记和排版兼容问题。

旧 Python 2 / Lua 构建和 SSH 发布脚本已移除，可从 Git 历史查看。

Lua 5.4 GC 插图和旧新浪插件演示 GIF 均已迁到本地，阅读时无需访问原图床。
