# Slidev 协作样稿

四页小样用于验证编辑与预览，还不是完整汇报稿。

## 语法指南与练习骨架

新手指南见 [Slidev 写作与展示指南](./guide/Slidev写作与展示指南.md)，可运行的六页骨架为 `guide/skeleton.md`。

在当前目录执行 `npm run dev:guide`，打开 http://localhost:3031 。它与原样稿的 3030 端口分开，使用 `guide/style.css` 和 `guide/public/`，适合独立练习。

## 启动

在此目录打开终端，首次安装后运行：

```powershell
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:3030 。右方向键或空格逐步展示／切页，左方向键回退。页面底部悬浮工具栏也提供导航。

## 如何一起修改

- `slides.md`：页面内容、分页、代码、逐步出现和演讲备注。
- `style.css`：颜色、字号、间距等公共样式。
- `public/candidates.html`：现有项目渲染器生成的空看板副本，仅用于展示布局，不包含真实岗位。

在 VS Code 打开 `slides.md`，修改后保存，浏览器自动更新。可以让 AI 修改同一文件，避免同时编辑相同位置。项目梳理长文仍保留在 `docs/project-review/`。

本样稿第三页为简化教学代码。没有调用模型、联网搜索或发送邮件；打开仓库链接需要网络。DSH 实操需另行启动已安装的 DSH，没有假设固定服务地址。

## 构建

```powershell
npm run build
```

生成 `dist/`，需要通过静态服务器提供，不能假设双击 HTML 可运行。PDF 导出另需 Playwright 浏览器依赖，当前小样不以导出作为验收目标。

`node_modules/`、`dist/` 及缓存不进入 Git。样稿源码、空看板副本与依赖锁文件加入仓库允许清单。
