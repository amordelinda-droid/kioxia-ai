
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="KIOXIA AI",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------
# UI styling
# ----------------------------
st.markdown("""
<style>
.block-container {max-width: 1100px; padding-top: 1.5rem; padding-bottom: 3rem;}
.k-card {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 22px;
    padding: 22px 24px;
    background: rgba(255,255,255,.03);
    margin-bottom: 16px;
}
.k-title {font-size: 34px; font-weight: 750; letter-spacing: 4px; text-align:center;}
.k-sub {font-size: 13px; opacity: .65; text-align:center; margin-top:4px;}
.k-big {font-size: 31px; font-weight: 760;}
.k-label {font-size: 13px; opacity: .7;}
.k-good {color:#20a464;}
.k-warn {color:#d69e2e;}
.k-bad {color:#d9534f;}
.k-muted {opacity:.72;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.2);
    padding: 14px 16px;
    border-radius: 18px;
}

@media (max-width: 700px) {
    .block-container {padding: 0.8rem 0.7rem 2rem 0.7rem !important;}
    .k-title {font-size: 27px !important; letter-spacing: 2px !important;}
    .k-card {padding: 17px 16px !important; border-radius: 18px !important;}
    .k-big {font-size: 26px !important;}
    div[data-testid="stMetric"] {padding: 10px 11px !important;}
    div[data-testid="stMetricValue"] {font-size: 1.35rem !important;}
    button[data-baseweb="tab"] {font-size: 0.82rem !important; padding-left: 8px !important; padding-right: 8px !important;}
}

</style>
""", unsafe_allow_html=True)

# ----------------------------
# Configuration
# ----------------------------
DEFAULT_HOLDINGS = [
    {"shares": 100, "cost": 43980},
    {"shares": 100, "cost": 68380},
    {"shares": 100, "cost": 75520},
    {"shares": 100, "cost": 58900},
]

RELATED = {
    "Sandisk": "SNDK",
    "Micron": "MU",
    "SOX": "^SOX",
}

def weighted_avg_cost(rows):
    total_shares = sum(r["shares"] for r in rows)
    total_cost = sum(r["shares"] * r["cost"] for r in rows)
    return total_shares, total_cost / total_shares if total_shares else 0

@st.cache_data(ttl=900, show_spinner=False)
def load_price_data(ticker: str, period="1y", interval="1d"):
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.dropna(how="all")
    return df

@st.cache_data(ttl=900, show_spinner=False)
def load_related_snapshot():
    out = {}
    for name, ticker in RELATED.items():
        try:
            df = load_price_data(ticker, period="10d", interval="1d")
            if len(df) >= 2:
                last = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2])
                chg = (last / prev - 1) * 100
                out[name] = {"price": last, "change": chg}
            else:
                out[name] = {"price": np.nan, "change": np.nan}
        except Exception:
            out[name] = {"price": np.nan, "change": np.nan}
    return out

def add_indicators(df):
    x = df.copy()
    for n in [5, 25, 75]:
        x[f"MA{n}"] = x["Close"].rolling(n).mean()

    # GMMA-like ribbon, 5 to 75 days
    periods = np.unique(np.linspace(5, 75, 15).round().astype(int))
    for p in periods:
        x[f"GMMA_{p}"] = x["Close"].ewm(span=int(p), adjust=False).mean()

    ema12 = x["Close"].ewm(span=12, adjust=False).mean()
    ema26 = x["Close"].ewm(span=26, adjust=False).mean()
    x["MACD"] = ema12 - ema26
    x["Signal"] = x["MACD"].ewm(span=9, adjust=False).mean()
    x["Hist"] = x["MACD"] - x["Signal"]

    delta = x["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    x["RSI"] = 100 - (100 / (1 + rs))

    x["VolAvg20"] = x["Volume"].rolling(20).mean()
    return x

def classify_related(change):
    if pd.isna(change):
        return "⚪ 数据不足", "k-muted"
    if change >= 1.0:
        return "🟢 利多", "k-good"
    if change <= -1.0:
        return "🔴 利空", "k-bad"
    return "🟡 中性", "k-warn"

def make_score(df, related):
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    tech = 50
    reasons = []

    # Price vs MAs
    for n, pts in [(5, 8), (25, 10), (75, 8)]:
        ma = last.get(f"MA{n}", np.nan)
        if not pd.isna(ma):
            if last["Close"] > ma:
                tech += pts
                reasons.append(f"股价站上{n}日均线")
            else:
                tech -= pts // 2

    # MACD
    macd_up = last["MACD"] > prev["MACD"]
    hist_up = last["Hist"] > prev["Hist"]
    golden = last["MACD"] > last["Signal"]
    if golden:
        tech += 12
        reasons.append("MACD位于Signal上方")
    elif macd_up or hist_up:
        tech += 6
        reasons.append("MACD动能改善")
    else:
        tech -= 6

    # Volume
    if not pd.isna(last["VolAvg20"]) and last["Volume"] > last["VolAvg20"] * 1.3:
        if last["Close"] >= prev["Close"]:
            tech += 10
            reasons.append("上涨伴随放量")
        else:
            tech -= 12
            reasons.append("放量下跌")

    # RSI
    if not pd.isna(last["RSI"]):
        if 45 <= last["RSI"] <= 68:
            tech += 5
        elif last["RSI"] >= 78:
            tech -= 8
            reasons.append("RSI偏热")
        elif last["RSI"] <= 30:
            tech += 2
            reasons.append("RSI进入超卖区")

    industry = 50
    for v in related.values():
        c = v["change"]
        if pd.isna(c):
            continue
        industry += np.clip(c, -5, 5) * 2
    industry = int(np.clip(industry, 0, 100))
    tech = int(np.clip(tech, 0, 100))

    # Free version has no audited fundamental feed; keep neutral base.
    fundamental = 70
    total = round(0.58 * tech + 0.27 * industry + 0.15 * fundamental)
    total = int(np.clip(total, 0, 100))

    if total >= 72:
        advice = "继续持有"
        color = "k-good"
        stars = "★★★★☆" if total < 88 else "★★★★★"
    elif total >= 52:
        advice = "提高警惕"
        color = "k-warn"
        stars = "★★★☆☆"
    else:
        advice = "考虑降低风险"
        color = "k-bad"
        stars = "★★☆☆☆"

    return {
        "score": total,
        "tech": tech,
        "industry": industry,
        "fundamental": fundamental,
        "advice": advice,
        "color": color,
        "stars": stars,
        "reasons": reasons[:4],
    }

def signal_arrow(now, prev, positive_is_up=True):
    if pd.isna(now) or pd.isna(prev):
        return "→"
    if now > prev:
        return "▲" if positive_is_up else "▼"
    if now < prev:
        return "▼" if positive_is_up else "▲"
    return "→"

def fmt_yen(x):
    if pd.isna(x):
        return "—"
    return f"¥{x:,.0f}"

def make_chart(df):
    show = df.tail(180).copy()
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.52, 0.15, 0.19, 0.14],
        specs=[[{"secondary_y": False}], [{}], [{}], [{}]]
    )

    fig.add_trace(go.Candlestick(
        x=show.index,
        open=show["Open"], high=show["High"],
        low=show["Low"], close=show["Close"],
        name="K线"
    ), row=1, col=1)

    for n in [5, 25, 75]:
        fig.add_trace(go.Scatter(
            x=show.index, y=show[f"MA{n}"],
            mode="lines", name=f"MA{n}", line={"width": 1.5}
        ), row=1, col=1)

    # GMMA ribbon
    gmma_cols = [c for c in show.columns if c.startswith("GMMA_")]
    for c in gmma_cols:
        fig.add_trace(go.Scatter(
            x=show.index, y=show[c], mode="lines",
            name=c, line={"width": 0.6}, opacity=0.25,
            showlegend=False
        ), row=1, col=1)

    fig.add_trace(go.Bar(x=show.index, y=show["Volume"], name="成交量"), row=2, col=1)
    fig.add_trace(go.Scatter(x=show.index, y=show["MACD"], mode="lines", name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=show.index, y=show["Signal"], mode="lines", name="Signal"), row=3, col=1)
    fig.add_trace(go.Bar(x=show.index, y=show["Hist"], name="Histogram"), row=3, col=1)
    fig.add_trace(go.Scatter(x=show.index, y=show["RSI"], mode="lines", name="RSI"), row=4, col=1)
    fig.add_hline(y=70, line_dash="dash", opacity=.35, row=4, col=1)
    fig.add_hline(y=30, line_dash="dash", opacity=.35, row=4, col=1)

    fig.update_layout(
        height=900,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_rangeslider_visible=False,
        legend_orientation="h",
        legend_y=1.02,
        hovermode="x unified",
    )
    return fig

# ----------------------------
# Sidebar settings
# ----------------------------
with st.sidebar:
    st.header("设置")
    ticker = st.text_input("股票代码", value="285A.T")
    st.caption("默认：Kioxia Holdings（东京证券交易所）")

    st.subheader("持仓")
    holdings = []
    defaults = DEFAULT_HOLDINGS
    for i, d in enumerate(defaults, start=1):
        c1, c2 = st.columns(2)
        shares = c1.number_input(f"第{i}笔股数", min_value=0, value=int(d["shares"]), step=100)
        cost = c2.number_input(f"第{i}笔成本", min_value=0, value=int(d["cost"]), step=10)
        holdings.append({"shares": shares, "cost": cost})

    refresh = st.button("重新抓取数据", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

# ----------------------------
# Data load
# ----------------------------
st.markdown('<div class="k-title">KIOXIA AI</div>', unsafe_allow_html=True)
st.markdown('<div class="k-sub">AI Decision Dashboard · 免费版 V1.0</div>', unsafe_allow_html=True)

try:
    raw = load_price_data(ticker, period="1y", interval="1d")
    if raw.empty:
        raise ValueError("没有获取到行情数据")
    df = add_indicators(raw)
    related = load_related_snapshot()
    result = make_score(df, related)
    last = df.iloc[-1]
    prev = df.iloc[-2]
except Exception as e:
    st.error(f"无法获取行情：{e}")
    st.info("免费行情源偶尔会短暂失效。请稍后点击左侧“重新抓取数据”，或检查股票代码是否为 285A.T。")
    st.stop()

shares, avg_cost = weighted_avg_cost(holdings)
current_price = float(last["Close"])
pnl = (current_price - avg_cost) * shares
pnl_pct = (current_price / avg_cost - 1) * 100 if avg_cost else 0
recovery_needed = (avg_cost / current_price - 1) * 100 if current_price else np.nan

# ----------------------------
# Main dashboard
# ----------------------------
st.markdown(f"""
<div class="k-card" style="text-align:center;">
  <div class="k-label">🟢 今天建议</div>
  <div class="k-big {result['color']}">{result['advice']}</div>
  <div style="font-size:22px; margin-top:6px;">{result['stars']}</div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("AI评分", f"{result['score']} 分", delta=f"技术 {result['tech']}")
c2.metric("当前价格", fmt_yen(current_price), delta=f"{(current_price/float(prev['Close'])-1)*100:+.2f}%")
c3.metric("距离回本", f"{max(recovery_needed, 0):.1f}%", delta=f"平均成本 {fmt_yen(avg_cost)}", delta_color="off")

st.markdown("### 今天变化")
a, b, c = st.columns(3)
a.metric("MACD", signal_arrow(last["MACD"], prev["MACD"]), delta=f"{last['MACD']:.2f}")
short_cols = [col for col in df.columns if col.startswith("GMMA_")]
short_col = sorted(short_cols, key=lambda x:int(x.split("_")[1]))[0]
a_gmma_now = last[short_col]
a_gmma_prev = prev[short_col]
b.metric("GMMA", signal_arrow(a_gmma_now, a_gmma_prev), delta=f"短均线 {fmt_yen(a_gmma_now)}")
vol_ratio = last["Volume"] / last["VolAvg20"] if not pd.isna(last["VolAvg20"]) and last["VolAvg20"] else np.nan
c.metric("成交量", "★★★★★" if vol_ratio >= 1.5 else "★★★☆☆", delta=f"{vol_ratio:.2f}×20日均量" if not pd.isna(vol_ratio) else "数据不足")

st.markdown("### 行业联动")
cols = st.columns(3)
for col, (name, v) in zip(cols, related.items()):
    label, css = classify_related(v["change"])
    col.markdown(f"""
    <div class="k-card">
      <div class="k-label">{name}</div>
      <div class="k-big {css}" style="font-size:22px;">{label}</div>
      <div class="k-muted">{v['change']:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("### 我的仓位")
p1, p2, p3, p4 = st.columns(4)
p1.metric("持股", f"{shares:,} 股")
p2.metric("平均成本", fmt_yen(avg_cost))
p3.metric("当前盈亏", fmt_yen(pnl), delta=f"{pnl_pct:+.2f}%")
p4.metric("回本价", fmt_yen(avg_cost))

st.markdown("### 🤖 为什么？")
reason_text = "；".join(result["reasons"]) if result["reasons"] else "技术指标暂时没有形成强烈共振"
st.info(f"{result['advice']}。当前技术评分 {result['tech']}，行业联动评分 {result['industry']}。主要依据：{reason_text}。")

tab1, tab2, tab3 = st.tabs(["📈 技术图表", "📊 评分明细", "🧮 做T参考"])

with tab1:
    st.plotly_chart(make_chart(df), use_container_width=True)
    st.caption("免费行情通常为延迟行情或收盘数据，不适合秒级交易。")

with tab2:
    score_df = pd.DataFrame({
        "维度": ["技术面", "行业联动", "基本面占位"],
        "分数": [result["tech"], result["industry"], result["fundamental"]],
        "权重": ["58%", "27%", "15%"],
    })
    st.dataframe(score_df, use_container_width=True, hide_index=True)
    st.warning("V1.0 的基本面分数暂用中性偏正面占位。后续版本再接入IR、财报和新闻解析。")

with tab3:
    recent = df.tail(60)
    support = float(recent["Low"].rolling(10).min().iloc[-1])
    resistance = float(recent["High"].rolling(20).max().iloc[-1])
    t1, t2, t3 = st.columns(3)
    t1.metric("短线支撑参考", fmt_yen(support))
    t2.metric("短线压力参考", fmt_yen(resistance))
    t3.metric("核心/机动仓", "300 / 100 股")
    st.caption("做T参考仅用于辅助判断，不构成交易指令。免费日线数据不适合盘中精确做T。")

st.divider()
st.caption(
    f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}｜"
    "数据源：Yahoo Finance（yfinance）｜本工具仅供投资研究，不保证数据完整或投资结果。"
)
