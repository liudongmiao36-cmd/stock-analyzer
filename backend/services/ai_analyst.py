import anthropic
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_analysis(
    symbol: str,
    name: str,
    latest: dict,
    sr: dict,
    positions: list,
) -> str:
    """Generate AI technical analysis report using Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        return "<p class='warn'>⚠️ 未配置 ANTHROPIC_API_KEY，无法生成AI分析。请在 .env 文件中填入你的 API Key。</p>"

    def fmt(v, decimals=2):
        return f"{v:.{decimals}f}" if v is not None else "N/A"

    # Build TA summary for prompt
    price = latest.get("price", 0)
    change = latest.get("change_pct", 0)
    rsi14 = latest.get("rsi14")
    rsi6 = latest.get("rsi6")
    kdj_k = latest.get("kdj_k")
    kdj_d = latest.get("kdj_d")
    kdj_j = latest.get("kdj_j")
    macd = latest.get("macd")
    macd_sig = latest.get("macd_signal")
    macd_hist = latest.get("macd_hist")
    bb_upper = latest.get("bb_upper")
    bb_middle = latest.get("bb_middle")
    bb_lower = latest.get("bb_lower")

    ema_arr = [
        ("EMA5", latest.get("ema5")),
        ("EMA10", latest.get("ema10")),
        ("EMA20", latest.get("ema20")),
        ("EMA60", latest.get("ema60")),
    ]
    ema_lines = []
    for label, val in ema_arr:
        if val:
            diff = (price - val) / val * 100
            pos = "上方" if price > val else "下方"
            ema_lines.append(f"{label}: {fmt(val)}（价格偏离 {pos} {abs(diff):.1f}%）")

    resistance = sr.get("resistance", [])
    support = sr.get("support", [])

    position_info = ""
    if positions:
        lines = []
        for p in positions:
            pnl = (price - p["cost_price"]) / p["cost_price"] * 100 if p["cost_price"] else 0
            sign = "+" if pnl >= 0 else ""
            lines.append(
                f"- 成本 {fmt(p['cost_price'])} × {p['quantity']}股，"
                f"当前浮动盈亏: {sign}{pnl:.1f}%"
                + (f"，备注: {p['notes']}" if p.get("notes") else "")
            )
        position_info = "## 持仓情况\n" + "\n".join(lines)

    prompt = f"""你是一位专业的A股技术分析师。请基于下方数据，对 {name}（{symbol}）进行全面的技术面综合分析。

## 最新行情
- 当前价格: {fmt(price)}  今日涨跌幅: {change:+.2f}%

## 均线系统
{chr(10).join(ema_lines) if ema_lines else "数据不足"}

## MACD（12,26,9）
- MACD: {fmt(macd)}  Signal: {fmt(macd_sig)}  柱状量: {fmt(macd_hist)}
- 状态: {"金叉形态" if macd and macd_sig and macd > macd_sig else "死叉形态" if macd and macd_sig and macd < macd_sig else "中性"}

## RSI
- RSI(14): {fmt(rsi14, 1)}  RSI(6): {fmt(rsi6, 1)}

## KDJ（9,3,3）
- K: {fmt(kdj_k, 1)}  D: {fmt(kdj_d, 1)}  J: {fmt(kdj_j, 1)}

## 布林带（20,2）
- 上轨: {fmt(bb_upper)}  中轨: {fmt(bb_middle)}  下轨: {fmt(bb_lower)}
- 价格位置: {"上轨附近，超买区" if bb_upper and price > bb_upper * 0.99 else "下轨附近，超卖区" if bb_lower and price < bb_lower * 1.01 else "布林带中部运行"}

## 关键价位
- 压力位: {', '.join([fmt(r) for r in resistance]) if resistance else "暂无明显压力位"}
- 支撑位: {', '.join([fmt(s) for s in support]) if support else "暂无明显支撑位"}

{position_info}

请按以下结构输出HTML格式的分析报告（只用 h4/p/ul/li/span 标签，不要加任何 class）：

<h4>一、趋势判断</h4>
<p>...</p>

<h4>二、指标信号综合</h4>
<ul><li>MACD: ...</li><li>RSI: ...</li><li>KDJ: ...</li><li>布林带: ...</li></ul>

<h4>三、关键价位分析</h4>
<p>...</p>

<h4>四、操作思路</h4>
<p>（结合持仓成本给出具体建议，如无持仓则给出入场参考价位）</p>

<h4>五、风险提示</h4>
<p>...</p>

要求：语言专业简洁，总字数500字以内。文末必须注明"以上为技术面分析参考，不构成投资建议。"
"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except anthropic.AuthenticationError:
        return "<p class='warn'>⚠️ API Key 无效，请检查 .env 中的 ANTHROPIC_API_KEY。</p>"
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return f"<p class='warn'>⚠️ 分析生成失败: {str(e)}</p>"
