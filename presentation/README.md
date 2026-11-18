# Slidev 汇报

两位同学的内容已经放入同一份汇报：引入、框架与技术、功能实操、局限与改进、总结。统一入口是 `demo/main.md`，沿用浅绿色主题和人物素材。

## 启动汇报

在 `presentation` 文件夹内执行：

```bash
npm ci
npm run dev:demo
```

打开 http://localhost:3032 。首次安装后，后续运行通常只需要 `npm run dev:demo`。右方向键或空格翻页；需要返回目录时可以在浏览器打开 `/agenda`。演讲者视图是 http://localhost:3032/presenter/，每页备注放在对应 Markdown 页面的 HTML 注释里。

构建使用 `npm run build:demo`。浏览器预览需要进程保持运行；导出为 PDF 或 PPTX 时，点击和动画等交互可能不能保留，应在展示设备上检查。

## 内容放在哪里

- `demo/sections/01-intro.md`：封面、目录和引入。
- `demo/sections/02-architecture.md`：模型、DSH 和插件的分工，流程动画和可展开的核心代码。
- `demo/sections/03-demo.md`：两份虚构档案的对照、追问与实际操作。
- `demo/sections/04-limitations.md`：数据来源、当前局限和改进方向。
- `demo/sections/05-closing.md`：总结。
- `demo/style.css`：整套汇报的颜色和样式；`demo/public/` 放图片和字体。
- `demo/profiles/`：用于排练的虚构档案；它们不会自动写入正在使用的 DSH 数据目录。详细准备见 [汇报分工与实操脚本](./demo/汇报分工与实操脚本.md)。

`demo/components/` 是对 `components/` 中现有互动组件的引用，代码块使用 Shiki 为 JavaScript 和 Python 着色。动画、示意页面本身不会调用模型、搜索或读取用户档案；实际实操需要单独运行 DSH。模型是否调用工具取决于具体运行过程，示意路径和虚构档案用于讲解。

框架及局限页的人物图片来自 X 用户 [@mofuchen_fff 的第一组图片](https://x.com/mofuchen_fff/status/2121908726332543229)和[第二组图片](https://x.com/mofuchen_fff/status/2122632613722808783)，原图保存在 `demo/public/assets/`，供本次演示使用。

演讲者视图可同步翻页，但自定义按钮的展开状态不会自动同步：投屏时请在观众窗口操作互动内容。源码链接指向 GitHub 的 `main`，代码可能随仓库更新。

## 其他材料

- `slides.md` 和 `style.css`：早期协作样稿，可运行 `npm run dev`，使用 3030 端口。
- `guide/`：[Slidev 写作与展示指南](./guide/Slidev写作与展示指南.md)和练习骨架，运行 `npm run dev:guide`，使用 3031 端口。

演示内容、组件、锁文件和素材需要一起提交；`node_modules/`、构建产物、密钥和个人运行数据保留在本地。
