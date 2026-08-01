
# KIOXIA AI Monitor V1.0

一个面向 Kioxia Holdings（285A.T）的免费量化分析小工具。

## 已包含
- KIOXIA AI 首页
- 今日建议：继续持有 / 提高警惕 / 考虑降低风险
- AI 综合评分
- 5 / 25 / 75 日均线
- GMMA 均线带
- MACD / RSI / 成交量
- Sandisk / Micron / SOX 联动
- 400 股持仓盈亏与回本距离
- 简单支撑位、压力位和做T参考
- 免费行情源自动更新

## 安装

需要电脑安装 Python 3.10 或以上版本。

在终端进入本文件夹后执行：

```bash
pip install -r requirements.txt
streamlit run app.py
```

启动后浏览器会自动打开。

## Windows 快速启动

双击 `start_windows.bat`。

## macOS 快速启动

终端执行：

```bash
chmod +x start_mac.command
./start_mac.command
```

## 注意事项
- 免费行情可能延迟，偶尔也会临时无法连接。
- V1.0 适合收盘后趋势分析，不适合秒级或盘口交易。
- V1.0 的基本面评分暂时采用占位值；后续可接入IR、财报与新闻解析。
- 任何评分与信号都只是辅助研究，不构成投资建议。
