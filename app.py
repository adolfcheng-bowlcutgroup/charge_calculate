import streamlit as st
import pandas as pd
import openai

# --- 1. 頁面基礎設定 ---
st.set_page_config(page_title="雙軌制回饋分析模型 (AI 顧問版)", layout="wide")

st.markdown("""
<style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; }
    div[data-testid="stDataFrame"] { font-size: 1.1rem; }
    .big-font { font-size: 1.2rem; font-weight: bold; }
    .stButton button { width: 100%; background-color: #FF4B4B; color: white; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ 分潤試算工具 (AI 顧問版)")
st.markdown("""
本模型採 **雙軌疊加** 計算，表格下方提供 AI 智能分析：
1. **場地租金 (區間變數)**：依照 11 階層折扣率，計算場租節省區間。
2. **商品抽成 (獨立變數)**：依照設定的 **「減免百分比」**，計算固定節省金額與對分利潤。
""")

# --- 2. 側邊欄：參數設定 ---
with st.sidebar:
    st.header("🔑 OpenAI 設定")
    api_key = st.text_input("輸入 OpenAI API Key", type="password", help="請輸入您的 API Key 以啟用 AI 分析功能")
    
    st.divider()

    st.header("1. 營業預估收入 (Gross)")
    ticket_gross = st.number_input("🎫 票券營業額預估", value=14_400_000, step=100000, format="%d")
    merch_gross = st.number_input("🛍️ 商品營業額預估", value=15_000_000, step=100000, format="%d")
    
    st.divider()
    
    st.header("2. 原始成本 (Baseline)")
    base_rent = st.number_input("原定場租 (固定)", value=1_900_000, step=100000)
    base_rate_pct = st.number_input("原定商品抽成 (%)", value=3.0, step=0.1)
    base_rate = base_rate_pct / 100

    st.divider()

    st.header("3. 票券抽成（按目標）")
    st.info("請直接輸入百分比數值 (例如 6.5 代表 6.5%)")
    
    # 輸入框設定 (保留您的預設值)
    p0  = st.number_input("Lv0. 租金減免 0% (無折扣)",  min_value=0.0, max_value=100.0, value=6.0, step=0.1, format="%.2f") / 100
    p1  = st.number_input("Lv1. 租金減免 1~10%",      min_value=0.0, max_value=100.0, value=6.5, step=0.1, format="%.2f") / 100
    p2  = st.number_input("Lv2. 租金減免 11~20%",     min_value=0.0, max_value=100.0, value=7.0, step=0.1, format="%.2f") / 100
    p3  = st.number_input("Lv3. 租金減免 21~30%",     min_value=0.0, max_value=100.0, value=7.5, step=0.1, format="%.2f") / 100
    p4  = st.number_input("Lv4. 租金減免 31~40%",     min_value=0.0, max_value=100.0, value=8.0, step=0.1, format="%.2f") / 100
    p5  = st.number_input("Lv5. 租金減免 41~50%",     min_value=0.0, max_value=100.0, value=8.5, step=0.1, format="%.2f") / 100
    p6  = st.number_input("Lv6. 租金減免 51~60%",     min_value=0.0, max_value=100.0, value=9.0, step=0.1, format="%.2f") / 100
    p7  = st.number_input("Lv7. 租金減免 61~70%",     min_value=0.0, max_value=100.0, value=9.5, step=0.1, format="%.2f") / 100
    p8  = st.number_input("Lv8. 租金減免 71~80%",     min_value=0.0, max_value=100.0, value=10.0, step=0.1, format="%.2f") / 100
    p9  = st.number_input("Lv9. 租金減免 81~90%",     min_value=0.0, max_value=100.0, value=15.0, step=0.1, format="%.2f") / 100
    p10 = st.number_input("Lv10. 租金減免 91~100%",   min_value=0.0, max_value=100.0, value=15.0, step=0.1, format="%.2f") / 100

    st.divider()
    
    st.header("4. 商品抽成")
    
    merch_reduction_pct = st.number_input(
        "減免百分比 (%)", 
        min_value=0.0, 
        max_value=float(base_rate_pct), 
        value=0.0, 
        step=0.1,
        format="%.2f"
    )
    
    merch_savings_fixed = merch_gross * (merch_reduction_pct / 100)
    merch_payout_fixed = merch_savings_fixed / 2
    
    st.success(f"🛍️ 商品端預估：省下 ${merch_savings_fixed:,.0f} ⮕ 分潤 ${merch_payout_fixed:,.0f}")

# --- 3. 核心邏輯運算 ---

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
    rent_payout = ticket_gross * t["rent_payout_pct"]
    rent_savings_min = base_rent * t["min_disc"]
    rent_savings_max = base_rent * t["max_disc"]
    
    total_savings_min = rent_savings_min + merch_savings_fixed
    total_savings_max = rent_savings_max + merch_savings_fixed
    
    total_payout = rent_payout + merch_payout_fixed
    
    net_min = total_savings_min - total_payout
    net_max = total_savings_max - total_payout
    
    if net_min > 0:
        status = "✅ 絕對獲利"
        color = "#2ecc71"
    elif net_max < 0:
        status = "❌ 絕對虧損"
        color = "#e74c3c"
    else:
        status = "⚠️ 浮動風險"
        color = "#f1c40f"

    results.append({
        "等級": t["等級"],
        "場租折扣": f"{int(t['min_disc']*100)}%~{int(t['max_disc']*100)}%",
        "票券分潤%": f"{t['rent_payout_pct']*100:.1f}%",
        "總支付 Cost": total_payout,
        "總價值 Min": total_savings_min,
        "總價值 Max": total_savings_max,
        "淨效益 Min": net_min,
        "淨效益 Max": net_max,
        "狀態": status
    })

df = pd.DataFrame(results)

# --- 4. 介面呈現 ---

col1, col2, col3 = st.columns(3)
col1.metric("預估總營業額 (Gross)", f"${(ticket_gross + merch_gross):,.0f}")
col2.metric("Baseline 場地總成本", f"${(base_rent + (merch_gross * base_rate)):,.0f}")
col3.metric("商品減免設定", f"減免 {merch_reduction_pct}%")

st.divider()

# --- 移除圖表，只保留表格並上提 ---
st.subheader("📊 損益明細表")

# 準備顯示用的 DataFrame
display_df = df.copy()
display_df["淨效益區間"] = display_df.apply(lambda r: f"${r['淨效益 Min']:,.0f} ~ ${r['淨效益 Max']:,.0f}", axis=1)
display_df["總支付 Cost"] = display_df["總支付 Cost"].apply(lambda x: f"${x:,.0f}")
display_df["總價值 Min"] = display_df["總價值 Min"].apply(lambda x: f"${x:,.0f}")
display_df["總價值 Max"] = display_df["總價值 Max"].apply(lambda x: f"${x:,.0f}")

final_table = display_df[["等級", "場租折扣", "票券分潤%", "總支付 Cost", "總價值 Min", "總價值 Max", "淨效益區間", "狀態"]]

st.dataframe(
    final_table.style.applymap(lambda v: f"color: {v.split(' ')[0] if 'color' in v else 'black'}", subset=["狀態"]),
    use_container_width=True
)

st.divider()

# --- 新增 OpenAI 建議視窗 ---
st.subheader("🤖 AI 談判顧問建議")

# 檢查是否有輸入 API Key
if not api_key:
    st.warning("請先在左側欄位輸入 OpenAI API Key 才能啟用智能分析功能。")
else:
    if st.button("生成分析報告"):
        with st.spinner("AI 正在分析您的財務模型..."):
            try:
                # 1. 將 Dataframe 轉為 CSV 格式字串，讓 AI 讀取
                df_csv = df.to_csv(index=False)
                
                # 2. 構建 Prompt
                system_msg = "你是一位專業的財務談判顧問，擅長分析成本結構與商業損益。"
                user_msg = f"""
                以下是我們針對一個合作案的「雙軌制分潤模型」試算結果。
                
                **背景參數：**
                - 票券營收：{ticket_gross:,}
                - 原本場租：{base_rent:,}
                - 商品營收：{merch_gross:,}
                - 商品減免：{merch_reduction_pct}%
                
                **試算表數據 (Lv0~Lv10 代表場租折扣程度)：**
                {df_csv}
                
                **請幫我做以下分析 (請用繁體中文，條列式，語氣專業且直接)：**
                1. **總結現況**：目前的參數設定下，整體是偏向獲利還是虧損？
                2. **關鍵風險**：指出哪些等級(Level)是不合理的？(例如付出的分潤大於省下的錢)。
                3. **談判建議**：如果我要達到損益兩平或獲利，我應該調整哪個參數？(例如票券分潤%應該壓在多少以下？或是商品減免需要提升多少？)
                """

                # 3. 呼叫 OpenAI API
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o", # 或 gpt-3.5-turbo
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.7
                )
                
                # 4. 顯示結果
                analysis_content = response.choices[0].message.content
                st.markdown(analysis_content)
                
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")
