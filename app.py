import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
import numpy as np

# ===== 頁面設定 =====
st.set_page_config(
    page_title="台北停車場分析儀表板",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== 深色主題 CSS =====
st.markdown("""
<style>
    /* 主要背景和文字顏色 */
    .stApp {
        background-color: #0f172a;
    }
    
    /* 側邊欄樣式 */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #f1f5f9;
    }
    
    /* 標題區域 */
    .dashboard-header {
        background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 1.5rem;
        position: relative;
    }
    .dashboard-header h1 {
        color: white;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .dashboard-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    
    /* 指標卡片 */
    .metric-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #334155;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    .metric-card.cyan::before { background: linear-gradient(90deg, #22d3ee, transparent); }
    .metric-card.emerald::before { background: linear-gradient(90deg, #34d399, transparent); }
    .metric-card.rose::before { background: linear-gradient(90deg, #fb7185, transparent); }
    .metric-card.amber::before { background: linear-gradient(90deg, #fbbf24, transparent); }
    .metric-card.violet::before { background: linear-gradient(90deg, #a78bfa, transparent); }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-value.cyan { color: #22d3ee; }
    .metric-value.emerald { color: #34d399; }
    .metric-value.rose { color: #fb7185; }
    .metric-value.amber { color: #fbbf24; }
    .metric-value.violet { color: #a78bfa; }
    
    .metric-sub {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }
    
    /* 圖表卡片 */
    .chart-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #334155;
        margin-bottom: 1.5rem;
    }
    .chart-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .chart-title::before {
        content: '';
        display: inline-block;
        width: 4px;
        height: 20px;
        background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
        border-radius: 2px;
    }
    
    /* 控制面板 */
    .controls-panel {
        background: #1e293b;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #334155;
        margin-bottom: 1.5rem;
    }
    
    /* 圖例 */
    .legend-container {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        flex-wrap: wrap;
        margin-top: 1rem;
        padding: 0.5rem;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.8rem;
        color: #94a3b8;
    }
    .legend-color {
        width: 20px;
        height: 12px;
        border-radius: 3px;
    }
    
    /* 頁尾 */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #94a3b8;
        font-size: 0.85rem;
        border-top: 1px solid #334155;
        margin-top: 2rem;
    }
    
    /* Streamlit 元素覆寫 */
    .stSelectbox label, .stDateInput label, .stRadio label {
        color: #94a3b8 !important;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.85rem;
    }
    
    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Radio 按鈕樣式 */
    .stRadio > div {
        background: #0f172a;
        padding: 0.25rem;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ===== 連接 BigQuery =====
@st.cache_resource
def get_bigquery_client():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    return bigquery.Client(credentials=credentials)

client = get_bigquery_client()

# ===== 取得停車場清單 =====
@st.cache_data(ttl=3600)
def get_parking_lots():
    query = """
    SELECT parking_lot_id, name, area, total_cars, total_motor
    FROM `parking-history-taipei.taipei_parking.parking_lots`
    WHERE total_cars > 0
    ORDER BY name
    """
    return client.query(query).to_dataframe()

# ===== 取得停車資料 =====
@st.cache_data(ttl=300)
def get_parking_data(parking_lot_id, start_date, end_date, total_cars):
    query = f"""
    SELECT 
        DATETIME(record_time, 'Asia/Taipei') AS taipei_time,
        available_cars,
        {total_cars} AS total_cars,
        {total_cars} - available_cars AS used_cars,
        ROUND(({total_cars} - available_cars) / {total_cars} * 100, 1) AS usage_rate,
        EXTRACT(HOUR FROM DATETIME(record_time, 'Asia/Taipei')) AS hour,
        EXTRACT(DAYOFWEEK FROM DATETIME(record_time, 'Asia/Taipei')) AS day_of_week,
        FORMAT_DATETIME('%Y-%m-%d', DATETIME(record_time, 'Asia/Taipei')) AS date_str
    FROM `parking-history-taipei.taipei_parking.realtime_spots`
    WHERE parking_lot_id = '{parking_lot_id}'
        AND available_cars >= 0
        AND DATE(record_time, 'Asia/Taipei') BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY record_time
    """
    return client.query(query).to_dataframe()

# ===== 側邊欄：篩選條件 =====
with st.sidebar:
    st.markdown("### 🔍 篩選條件")
    
    # 取得停車場清單
    parking_lots = get_parking_lots()
    
    # 找出預設停車場的位置
    default_index = 0
    if 'TPE0410' in parking_lots['parking_lot_id'].values:
        matches = parking_lots[parking_lots['parking_lot_id'] == 'TPE0410'].index.tolist()
        if len(matches) > 0:
            default_index = parking_lots.index.get_loc(matches[0])
    
    # 停車場選擇器
    selected_lot_name = st.selectbox(
        "選擇停車場",
        parking_lots['name'].tolist(),
        index=default_index
    )
    
    # 取得選中停車場的資訊
    selected_lot = parking_lots[parking_lots['name'] == selected_lot_name].iloc[0]
    parking_lot_id = selected_lot['parking_lot_id']
    total_cars = int(selected_lot['total_cars'])
    total_motor = int(selected_lot['total_motor'])
    area = selected_lot['area']
    
    st.markdown("---")
    
    # 日期範圍選擇器
    st.markdown("##### 📅 資料期間")
    start_date = st.date_input(
        "開始日期",
        datetime.now() - timedelta(days=7)
    )
    end_date = st.date_input(
        "結束日期",
        datetime.now()
    )
    
    st.markdown("---")
    
    # 時間粒度選擇器
    time_granularity = st.radio(
        "時間粒度",
        ["5 分鐘", "15 分鐘", "30 分鐘", "1 小時", "4 小時"],
        index=0,
        horizontal=True
    )
    
    # 顯示指標選擇
    display_metric = st.radio(
        "顯示指標",
        ["剩餘車位", "使用率"],
        index=0,
        horizontal=True
    )

# ===== 讀取資料 =====
with st.spinner('載入資料中...'):
    df = get_parking_data(parking_lot_id, start_date, end_date, total_cars)

# ===== 標題區域 =====
st.markdown(f"""
<div class="dashboard-header">
    <h1>🅿️ {selected_lot_name}營運分析</h1>
    <p>{area} | 汽車車位：{total_cars}格 | 機車車位：{total_motor}格 | 資料期間：{start_date} - {end_date}</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("所選日期範圍內沒有資料，請調整日期範圍。")
    st.stop()

# ===== 計算統計數據 =====
avg_available = df['available_cars'].mean()
avg_usage = df['usage_rate'].mean()
max_available = df['available_cars'].max()
min_available = df['available_cars'].min()
max_usage = df['usage_rate'].max()
min_usage = df['usage_rate'].min()

# 找出最高和最低的時間點
max_idx = df['available_cars'].idxmax()
min_idx = df['available_cars'].idxmin()
max_time = pd.to_datetime(df.loc[max_idx, 'taipei_time']).strftime('%m/%d %H:%M')
min_time = pd.to_datetime(df.loc[min_idx, 'taipei_time']).strftime('%m/%d %H:%M')

# 計算尖峰時段 (使用率 > 60%)
hourly_avg = df.groupby('hour')['usage_rate'].mean()
peak_hours = hourly_avg[hourly_avg > 60].index.tolist()
if peak_hours:
    peak_hours_str = f"{min(peak_hours)}:00-{max(peak_hours)+1}:00"
else:
    peak_hours_str = "無"

# 計算週間 vs 週末
df['is_weekend'] = df['day_of_week'].isin([1, 7])  # 1=Sunday, 7=Saturday
weekday_avg = df[~df['is_weekend']]['usage_rate'].mean()
weekend_avg = df[df['is_weekend']]['usage_rate'].mean()

# ===== 關鍵指標卡片 =====
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card cyan">
        <div class="metric-label">平均剩餘車位</div>
        <div class="metric-value cyan">{avg_available:.0f}</div>
        <div class="metric-sub">平均使用率：{avg_usage:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card emerald">
        <div class="metric-label">最高剩餘車位</div>
        <div class="metric-value emerald">{max_available:.0f}</div>
        <div class="metric-sub">{max_time}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card rose">
        <div class="metric-label">最低剩餘車位（尖峰）</div>
        <div class="metric-value rose">{min_available:.0f}</div>
        <div class="metric-sub">{min_time}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card amber">
        <div class="metric-label">尖峰時段</div>
        <div class="metric-value amber">{peak_hours_str}</div>
        <div class="metric-sub">使用率 > 60%</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    diff = weekday_avg - weekend_avg
    diff_text = f"週間高 {abs(diff):.1f}%" if diff > 0 else f"週末高 {abs(diff):.1f}%"
    st.markdown(f"""
    <div class="metric-card violet">
        <div class="metric-label">週間 vs 週末</div>
        <div class="metric-value violet">{diff_text}</div>
        <div class="metric-sub">週間 {weekday_avg:.1f}% / 週末 {weekend_avg:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ===== Plotly 圖表配置 =====
plotly_layout = dict(
    paper_bgcolor='#1e293b',
    plot_bgcolor='#1e293b',
    font=dict(color='#94a3b8'),
    margin=dict(l=40, r=40, t=40, b=40),
    xaxis=dict(
        gridcolor='rgba(51, 65, 85, 0.5)',
        zerolinecolor='rgba(51, 65, 85, 0.5)'
    ),
    yaxis=dict(
        gridcolor='rgba(51, 65, 85, 0.5)',
        zerolinecolor='rgba(51, 65, 85, 0.5)'
    )
)

# ===== 根據時間粒度聚合資料 =====
granularity_map = {
    "5 分鐘": "5min",
    "15 分鐘": "15min",
    "30 分鐘": "30min",
    "1 小時": "1h",
    "4 小時": "4h"
}
gran = granularity_map[time_granularity]

df['taipei_time'] = pd.to_datetime(df['taipei_time'])
trend_df = df.set_index('taipei_time').resample(gran).agg({
    'available_cars': 'mean',
    'usage_rate': 'mean'
}).reset_index()
trend_df.columns = ['time', 'available', 'usage_rate']

# ===== 主趨勢圖 =====
st.markdown("""
<div class="chart-card">
    <div class="chart-title">剩餘車位趨勢圖</div>
</div>
""", unsafe_allow_html=True)

if display_metric == "剩餘車位":
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(
        x=trend_df['time'],
        y=trend_df['available'],
        mode='lines',
        fill='tozeroy',
        line=dict(color='#22d3ee', width=2),
        fillcolor='rgba(34, 211, 238, 0.1)',
        name='剩餘車位'
    ))
    fig_main.update_layout(
        **plotly_layout,
        height=400,
        yaxis_title='剩餘車位',
        xaxis_title='時間',
        yaxis=dict(
            gridcolor='rgba(51, 65, 85, 0.5)',
            range=[0, total_cars * 1.1]
        ),
        hovermode='x unified'
    )
else:
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(
        x=trend_df['time'],
        y=trend_df['usage_rate'],
        mode='lines',
        fill='tozeroy',
        line=dict(color='#22d3ee', width=2),
        fillcolor='rgba(34, 211, 238, 0.1)',
        name='使用率'
    ))
    fig_main.update_layout(
        **plotly_layout,
        height=400,
        yaxis_title='使用率 (%)',
        xaxis_title='時間',
        yaxis=dict(
            gridcolor='rgba(51, 65, 85, 0.5)',
            range=[0, 105]
        ),
        hovermode='x unified'
    )

st.plotly_chart(fig_main, use_container_width=True)

# ===== 雙圖表區：時段分析 + 每日比較 =====
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">各時段平均使用率</div>
    </div>
    """, unsafe_allow_html=True)
    
    hourly_df = df.groupby('hour').agg({'usage_rate': 'mean'}).reset_index()
    
    fig_hourly = go.Figure()
    fig_hourly.add_trace(go.Bar(
        x=hourly_df['hour'],
        y=hourly_df['usage_rate'],
        marker=dict(
            color='#22d3ee',
            cornerradius=6
        ),
        name='使用率'
    ))
    fig_hourly.update_layout(
        **plotly_layout,
        height=350,
        yaxis_title='平均使用率 (%)',
        xaxis_title='小時',
        xaxis=dict(
            tickmode='linear',
            tick0=0,
            dtick=2,
            gridcolor='rgba(51, 65, 85, 0.5)'
        ),
        yaxis=dict(
            gridcolor='rgba(51, 65, 85, 0.5)',
            range=[0, 100]
        )
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

with col_right:
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">每日使用率比較</div>
    </div>
    """, unsafe_allow_html=True)
    
    daily_df = df.groupby(['date_str', 'day_of_week']).agg({'usage_rate': 'mean'}).reset_index()
    daily_df['is_weekend'] = daily_df['day_of_week'].isin([1, 7])
    day_names = ['', '日', '一', '二', '三', '四', '五', '六']
    daily_df['label'] = daily_df.apply(
        lambda x: f"{x['date_str'][5:]} ({day_names[int(x['day_of_week'])]})", axis=1
    )
    
    # 週末用紫色，週間用青色
    colors = ['#a78bfa' if w else '#22d3ee' for w in daily_df['is_weekend']]
    
    fig_daily = go.Figure()
    fig_daily.add_trace(go.Bar(
        x=daily_df['label'],
        y=daily_df['usage_rate'],
        marker=dict(
            color=colors,
            cornerradius=6
        ),
        name='使用率'
    ))
    fig_daily.update_layout(
        **plotly_layout,
        height=350,
        yaxis_title='平均使用率 (%)',
        xaxis_title='日期',
        xaxis=dict(
            gridcolor='rgba(51, 65, 85, 0.5)',
            tickangle=-45
        ),
        yaxis=dict(
            gridcolor='rgba(51, 65, 85, 0.5)',
            range=[0, 100]
        )
    )
    st.plotly_chart(fig_daily, use_container_width=True)

# ===== 熱力圖 =====
st.markdown("""
<div class="chart-card">
    <div class="chart-title">使用率熱力圖（按日期×時段）</div>
</div>
""", unsafe_allow_html=True)

# 建立熱力圖資料
heatmap_data = df.groupby(['date_str', 'hour']).agg({'usage_rate': 'mean'}).reset_index()
heatmap_pivot = heatmap_data.pivot(index='date_str', columns='hour', values='usage_rate')

# 自定義色階：綠 -> 黃 -> 橙 -> 紅
custom_colorscale = [
    [0.0, '#22c55e'],    # 低使用率 - 綠
    [0.30, '#84cc16'],   # 中低 - 黃綠
    [0.45, '#eab308'],   # 中等 - 黃
    [0.55, '#f97316'],   # 中高 - 橙
    [0.65, '#ef4444'],   # 高 - 紅
    [1.0, '#dc2626']     # 非常高 - 深紅
]

fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_pivot.values,
    x=heatmap_pivot.columns,
    y=heatmap_pivot.index,
    colorscale=custom_colorscale,
    zmin=0,
    zmax=100,
    colorbar=dict(
        title='使用率 (%)',
        titleside='right',
        tickcolor='#94a3b8',
        tickfont=dict(color='#94a3b8')
    ),
    hovertemplate='日期: %{y}<br>時段: %{x}:00<br>使用率: %{z:.1f}%<extra></extra>'
))

fig_heatmap.update_layout(
    **plotly_layout,
    height=max(300, len(heatmap_pivot) * 25),
    xaxis_title='小時',
    yaxis_title='日期',
    xaxis=dict(
        tickmode='linear',
        tick0=0,
        dtick=1,
        gridcolor='rgba(51, 65, 85, 0.5)'
    ),
    yaxis=dict(
        gridcolor='rgba(51, 65, 85, 0.5)',
        autorange='reversed'
    )
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# 圖例
st.markdown("""
<div class="legend-container">
    <div class="legend-item">
        <div class="legend-color" style="background: #22c55e;"></div>
        <span>低使用率 (0-30%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #84cc16;"></div>
        <span>中低 (30-45%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #eab308;"></div>
        <span>中等 (45-55%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #f97316;"></div>
        <span>中高 (55-65%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #ef4444;"></div>
        <span>高使用率 (>65%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ===== 週間 vs 週末 24小時曲線 =====
st.markdown("""
<div class="chart-card">
    <div class="chart-title">週間 vs 週末 24小時使用率曲線</div>
</div>
""", unsafe_allow_html=True)

# 計算週間和週末的每小時平均
df['is_weekend'] = df['day_of_week'].isin([1, 7])
weekday_hourly = df[~df['is_weekend']].groupby('hour')['usage_rate'].mean().reset_index()
weekend_hourly = df[df['is_weekend']].groupby('hour')['usage_rate'].mean().reset_index()

fig_ww = go.Figure()

# 週間曲線
fig_ww.add_trace(go.Scatter(
    x=weekday_hourly['hour'],
    y=weekday_hourly['usage_rate'],
    mode='lines',
    fill='tozeroy',
    line=dict(color='#22d3ee', width=2),
    fillcolor='rgba(34, 211, 238, 0.1)',
    name='週間平均'
))

# 週末曲線
fig_ww.add_trace(go.Scatter(
    x=weekend_hourly['hour'],
    y=weekend_hourly['usage_rate'],
    mode='lines',
    fill='tozeroy',
    line=dict(color='#a78bfa', width=2),
    fillcolor='rgba(167, 139, 250, 0.1)',
    name='週末平均'
))

fig_ww.update_layout(
    **plotly_layout,
    height=350,
    xaxis_title='小時',
    yaxis_title='使用率 (%)',
    xaxis=dict(
        tickmode='linear',
        tick0=0,
        dtick=2,
        gridcolor='rgba(51, 65, 85, 0.5)'
    ),
    yaxis=dict(
        gridcolor='rgba(51, 65, 85, 0.5)',
        range=[0, 100]
    ),
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='center',
        x=0.5,
        font=dict(color='#94a3b8')
    ),
    hovermode='x unified'
)

st.plotly_chart(fig_ww, use_container_width=True)

# ===== 頁尾 =====
st.markdown(f"""
<div class="footer">
    資料更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
    資料範圍：{start_date} 至 {end_date} | 
    共 {len(df):,} 筆資料
</div>
""", unsafe_allow_html=True)
