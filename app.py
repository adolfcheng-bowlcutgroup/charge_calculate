import streamlit as st
import pandas as pd
import altair as alt

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="雙軌制回饋分析模型 (11階層版)", layout="wide")

st.markdown("""
<style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; }
    div[data-testid="stDataFrame"] { font-size: 1.1rem; }
    .big-font { font-size: 1.2rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ 分潤試算工具 (11階層版)")
st.markdown("""
本模型採 **雙軌疊加** 計算：
1. **場地租金 (區間變數)**：依照 11 階層折扣率，計算場租節省區間。
2. **商品抽成 (獨立變數)**：依照設定的 **「減免百分比」**，計算固定節省金額與對分利潤。
""")

# --- 2. 側邊欄：參數設定 ---
with st.sidebar:
    st.header("1. 營業預估收入 (Gross)")
    ticket_gross = st.number_input("🎫 票券營業額預估", value=15_000_000, step=500000, format="%d")
    merch_gross = st.number_input("🛍️ 商品營業額預估", value=15_000_000, step=500000, format="%d")
    
    st.divider()
    
    st.header("2. 原始成本 (Baseline)")
    base_rent = st.number_input("原定場租 (固定)", value=2_000_000, step=100000)
    base_rate_pct = st.number_input("原定商品抽成 (%)", value=3.0, step=0.1)
    base_rate = base_rate_pct / 100

    st.divider()

    st.header("3. 票券抽成（按目標）")
    st.info("設定各等級下，撥出多少 **票券營收** 給對方")
    
    # --- 修改部分：所有滑桿上限統一為 20.0 ---
    p0  = st.slider("Lv0. 租金減免 0% (無折扣)", 0.0, 20.0, 0.0, 0.1) / 100
    p1  = st.slider("Lv1. 租金減免 1~10%", 0.0, 20.0, 0.5, 0.1) / 100
    p2  = st.slider("Lv2. 租金減免 11~20%", 0.0, 20.0, 1.0, 0.1) / 100
    p3  = st.slider("Lv3. 租金減免 21~30%", 0.0, 20.0, 1.5, 0.1) / 100
    p4  = st.slider("Lv4. 租金減免 31~40%", 0.0, 20.0, 2.5, 0.1) / 100
    p5  = st.slider("Lv5. 租金減免 41~50%", 0.0, 20.0, 3.5, 0.1) / 100
    p6  = st.slider("Lv6. 租金減免 51~60%", 0.0, 20.0, 4.5, 0.1) / 100
    p7  = st.slider("Lv7. 租金減免 61~70%", 0.0, 20.0, 5.5, 0.1) / 100
    p8  = st.slider("Lv8. 租金減免 71~80%", 0.0, 20.0, 6.5, 0.1) / 100
    p9  = st.slider("Lv9. 租金減免 81~90%", 0.0, 20.0, 7.5, 0.1) / 100
    p10 = st.slider("Lv10. 租金減免 91~100%", 0.0, 20.0, 8.5, 0.1) / 100
    # --- 修改部分結束 ---

    st.divider()
    
    st.header("4. 商品抽成")
    st.markdown("設定 對方談到的 **抽成減免幅度**：")
    
    merch_reduction_pct = st.slider(
        "減免百分比 ", 
        min_value=0.0, 
        max_value=base_rate_pct, 
        value=1.0, 
        step=0.1,
        format="%.1f%%"
    )
    
    # 計算商品端的固定價值與回饋
    merch_savings_fixed = merch_gross * (merch_reduction_pct / 100)
    merch_payout_fixed = merch_savings_fixed / 2
    
    st.success(f"🛍️ 商品端預估：省下 ${merch_savings_fixed:,.0f} ⮕ 分潤 ${merch_payout_fixed:,.0f}")

# --- 3. 核心邏輯運算 ---

# 定義場租區間 (Lv0 ~ Lv10)
tiers_config = [
    {"等級": "Lv0",  "min_disc": 0.00, "max_disc": 0.00, "rent_payout_pct": p0},
    {"等級": "Lv1",  "min_disc": 0.01, "max_disc": 0.10, "rent_payout_pct": p1},
    {"等級": "Lv2",  "min_disc": 0.11, "max_disc": 0.20, "rent_payout_pct": p2},
    {"等級": "Lv3",  "min_disc": 0.21, "max_disc": 0.30, "rent_payout_pct": p3},
    {"等級": "Lv4",  "min_disc": 0.31, "max_disc": 0.40, "rent_payout_pct": p4},
    {"等級": "Lv5",  "min_disc": 0.41, "max_disc": 0.50, "rent_payout_pct": p5},
    {"等級": "Lv6",  "min_disc": 0.51, "max_disc": 0.60, "rent_payout_pct": p6},
    {"等級": "Lv7",  "min_disc": 0.61, "max_disc": 0.70, "rent_payout_pct": p7},
    {"等級": "Lv8",  "min_disc": 0.71, "max_disc": 0.80, "rent_payout_pct": p8},
    {"等級": "Lv9",  "min_disc": 0.81, "max_disc": 0.90, "rent_payout_pct": p9},
    {"等級": "Lv10", "min_disc": 0.91, "max_disc": 1.00, "rent_payout_pct": p10},
]

results = []

for t in tiers_config:
    # --- 軌道一：場地租金 (變動區間) ---
    # 1. 票券分潤支付
    rent_payout = ticket_gross * t["rent_payout_pct"]
    
    # 2. 場租價值區間 (省下的租金)
    rent_savings_min = base_rent * t["min_disc"]
    rent_savings_max = base_rent * t["max_disc"]
    
    # --- 軌道二：商品抽成 (固定變數) ---
    # *註：這裡的數值來自側邊欄設定*
    
    # --- 總和計算 (疊加) ---
    # 總價值 (Min ~ Max)
    total_savings_min = rent_savings_min + merch_savings_fixed
    total_savings_max = rent_savings_max + merch_savings_fixed
    
    # 總支付 (Single Value)
    total_payout = rent_payout + merch_payout_fixed
    
    # 淨效益 (Min ~ Max)
    net_min = total_savings_min - total_payout
    net_max = total_savings_max - total_payout
    
    # 狀態判斷
    if net_min > 0:
        status = "✅ 絕對獲利"
        color = "#2ecc71" # Green
    elif net_max < 0:
        status = "❌ 絕對虧損"
        color = "#e74c3c" # Red
    else:
        status = "⚠️ 浮動風險"
        color = "#f1c40f" # Orange

    results.append({
        "等級": t["等級"],
        "場租折扣": f"{int(t['min_disc']*100)}%~{int(t['max_disc']*100)}%",
        "票券分潤": rent_payout,
        "商品分潤": merch_payout_fixed,
        "總支付 Cost": total_payout,
        "總價值 Min": total_savings_min,
        "總價值 Max": total_savings_max,
        "淨效益 Min": net_min,
        "淨效益 Max": net_max,
        "狀態": status,
        "Color": color
    })

df = pd.DataFrame(results)

# --- 4. 介面呈現 ---

col1, col2, col3 = st.columns(3)
col1.metric("預估總營業額 (Gross)", f"${(ticket_gross + merch_gross):,.0f}")
col2.metric("Baseline 場地總成本", f"${(base_rent + (merch_gross * base_rate)):,.0f}")
col3.metric("商品減免設定", f"減免 {merch_reduction_pct}%")

st.divider()

# --- Chart: 區間四象限圖 ---
st.subheader(f"🎯 情境分析 (當商品減免 {merch_reduction_pct}% 時)")

chart_data = df.copy()
max_val = max(chart_data["總支付 Cost"].max(), chart_data["總價值 Max"].max()) * 1.1

base = alt.Chart(chart_data).encode(
    x=alt.X('總支付 Cost', title='總支付成本 (票券分潤 + 商品對分)', scale=alt.Scale(domain=[0, max_val]))
)

# 1. 垂直線 (Range Bar)
rule = base.mark_rule(size=3).encode(
    y=alt.Y('總價值 Min', title='A公司創造總價值 (租金+商品)', scale=alt.Scale(domain=[0, max_val])),
    y2='總價值 Max',
    color=alt.Color('Color', scale=None),
    tooltip=['等級', '場租折扣', '狀態', '淨效益 Min', '淨效益 Max']
)

# 2. 端點
points_min = base.mark_point(filled=True, shape='triangle-down', size=100).encode(
    y='總價值 Min', color=alt.Color('Color', scale=None)
)
points_max = base.mark_point(filled=True, shape='triangle-up', size=100).encode(
    y='總價值 Max', color=alt.Color('Color', scale=None)
)

# 3. 文字
text = base.mark_text(dy=-15, align='center', fontSize=10, fontWeight='bold').encode(
    y='總價值 Max', text='等級'
)

# 4. 損益平衡線
line = alt.Chart(pd.DataFrame({'x': [0, max_val], 'y': [0, max_val]})).mark_rule(
    strokeDash=[5, 5], color='gray', opacity=0.5
).encode(x='x', y='y')

final_chart = (rule + points_min + points_max + text + line).properties(height=600).interactive()
st.altair_chart(final_chart, use_container_width=True)

# --- Table: 詳細數據 ---
st.subheader("📊 損益明細表")

# 格式化
display_df = df.copy()
display_df["淨效益區間"] = display_df.apply(lambda r: f"${r['淨效益 Min']:,.0f} ~ ${r['淨效益 Max']:,.0f}", axis=1)

final_table = display_df[["等級", "場租折扣", "票券分潤", "商品分潤", "總支付 Cost", "總價值 Min", "總價值 Max", "淨效益區間", "狀態"]]

st.dataframe(
    final_table.style.format({
        "票券分潤": "${:,.0f}",
        "商品分潤": "${:,.0f}",
        "總支付 Cost": "${:,.0f}",
        "總價值 Min": "${:,.0f}",
        "總價值 Max": "${:,.0f}",
    }).applymap(lambda v: f"color: {v.split(' ')[0] if 'color' in v else 'black'}", subset=["狀態"]),
    use_container_width=True
)

st.info(f"""
**💡 如何解讀此圖表：**
此圖表顯示在 **「商品抽成減免 {merch_reduction_pct}%」** 的前提下，不同 **場租談判結果 (Lv0~Lv10)** 的損益狀況。
* 由於等級劃分變細 (10%一階)，您可以更精準地看到獲利/虧損的轉折點 (Break-even Point) 發生在哪一個等級。
* Lv0 代表場租完全沒有折扣的基準點。
""")
