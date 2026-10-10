KIOXIA AI Beta v1 — GitHub Pages / iPhone PWA

最快部署：
1. 解压本 ZIP。
2. 打开 GitHub 仓库 amordelinda-droid/kioxia-ai。
3. Add file -> Upload files。
4. 把解压后的 4 个文件（index.html / manifest.webmanifest / sw.js / icon.svg）上传到仓库根目录，Commit changes。
5. Settings -> Pages -> Deploy from a branch -> main -> /(root) -> Save。
6. 等 1~3 分钟后，用 Safari 打开：
   https://amordelinda-droid.github.io/kioxia-ai/
7. Safari 分享按钮 -> 添加到主屏幕。

说明：
- 行情优先读取 Yahoo Finance 公开 chart 接口，5分钟自动刷新。
- 浏览器/接口若阻止跨域，会自动使用演示回退数据，保证页面可打开。
- AI评分是规则型技术评分，仅用于测试，不构成投资建议。
- 默认持仓：400股，成本价 65,000 日元/股；可在页面直接修改。
