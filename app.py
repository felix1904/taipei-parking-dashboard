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

# ===== 優化後的 CSS (高對比 + 大字體) =====
st.markdown("""
<style>
    /* 全局設定 */
    .stApp {
        background-color: #0f172a;
        color: #e2e8f0; /* 淺灰白文字 */
        font-size: 1.1rem; /* 基礎字體加大 */
    }
    
    /* 側邊欄 */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p {
        color: #e2e8f0 !important;
        font-size: 1rem !important;
    }
    
    /* 標題區域 */
    .dashboard-header {
        background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    .dashboard-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .dashboard-header p {
        color: rgba(255,255,255,0.95);
        font-size: 1.2rem;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    
    /* 指標卡片 */
    .metric-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #334155;
        position: relative;
        overflow: hidden;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 6px; /* 加粗頂部線條 */
    }
    .metric-card.cyan::before { background: linear-gradient(90deg, #22d3ee, transparent); }
    .metric-card.emerald::before { background: linear-gradient(90deg, #34d399, transparent); }
    .metric-card.rose::before { background: linear-gradient(90deg, #fb7185, transparent); }
    .metric-card.amber::before { background: linear-gradient(90deg, #fbbf24, transparent); }
    .metric-card.violet::before { background: linear-gradient(90deg, #a78bfa, transparent); }
    
    .metric-label {
        font-size: 1rem;
        color: #cbd5e1;
        margin-bottom: 0.5rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 2.4rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .metric-value.cyan { color: #22d3ee; }
    .metric-value.emerald { color: #34d399; }
    .metric-value.rose { color: #fb7185; }
    .metric-value.amber { color: #fbbf24; }
    .metric-value.violet { color: #a78bfa; }
    
    .metric-sub {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-top: 0.5rem;
    }
    
    /* 圖表容器 */
    .chart-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #334155;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .chart-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .chart-title::before {
        content: '';
        display: inline-block;
        width: 6px;
        height: 24px;
        background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
        border-radius: 4px;
    }
    
    /* 圖例容器 */
    .legend-container {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        flex-wrap: wrap;
        margin-top: 1.5rem;
        padding: 1rem;
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 0.95rem;
        color: #e2e8f0;
        font-weight: 500;
    }
    .legend-color {
        width: 24px;
        height: 16px;
        border-radius: 4px;
    }
    
    /* UI 元件覆寫 */
    .stSelectbox label, .stDateInput label, .stRadio label {
        color: #ffffff !important;
        font-weight: 600;
        font-size: 1.05rem !important;
    }
    .stRadio div[role="radiogroup"] label {
        color: #e2e8f0 !important;
        font-size: 1rem !important;
    }
    
    .footer {
        text-align: center;
        padding: 3rem 1rem;
        color: #64748b;
        font-size: 0.9rem;
        border-top: 1px solid #334155;
        margin-top: 3rem;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
    
    parking_lots = get_parking_lots()
    
    default_index = 0
    if 'TPE0410' in parking_lots['parking_lot_id'].values:
        matches = parking_lots[parking_lots['parking_lot_id'] == 'TPE0410'].index.tolist()
        if len(matches) > 0:
            default_index = parking_lots.index.get_loc(matches[0])
    
    selected_lot_name = st.selectbox(
        "選擇停車場",
        parking_lots['name'].tolist(),
        index=default_index
    )
    
    selected_lot = parking_lots[parking_lots['name'] == selected_lot_name].iloc[0]
    parking_lot_id = selected_lot['parking_lot_id']
    total_cars = int(selected_lot['total_cars'])
    total_motor = int(selected_lot['total_motor'])
    area = selected_lot['area']
    
    st.markdown("---")
    
    st.markdown("##### 📅 資料期間")
    start_date = st.date_input("開始日期", datetime.now() - timedelta(days=7))
    end_date = st.date_input("結束日期", datetime.now())
    
    st.markdown("---")
    
    time_granularity = st.radio(
        "時間粒度",
        ["5 分鐘", "15 分鐘", "30 分鐘", "1 小時", "4 小時"],
        index=0,
        horizontal=True
    )
    
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

# ===== 數據計算 =====
avg_available = df['available_cars'].mean()
avg_usage = df['usage_rate'].mean()
max_available = df['available_cars'].max()
min_available = df['available_cars'].min()
max_idx = df['available_cars'].idxmax()
min_idx = df['available_cars'].idxmin()
max_time = pd.to_datetime(df.loc[max_idx, 'taipei_time']).strftime('%m/%d %H:%M')
min_time = pd.to_datetime(df.loc[min_idx, 'taipei_time']).strftime('%m/%d %H:%M')

hourly_avg = df.groupby('hour')['usage_rate'].mean()
peak_hours = hourly_avg[hourly_avg > 80].index.tolist() # 將尖峰定義提高到 80%
if peak_hours:
    peak_hours_str = f"{min(peak_hours)}:00-{max(peak_hours)+1}:00"
else:
    peak_hours_str = "無"

df['is_weekend'] = df['day_of_week'].isin([1, 7])
weekday_avg = df[~df['is_weekend']]['usage_rate'].mean()
weekend_avg = df[df['is_weekend']]['usage_rate'].mean()
if pd.isna(weekday_avg): weekday_avg = 0
if pd.isna(weekend_avg): weekend_avg = 0

# ===== 指標卡片 =====
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
        <div class="metric-label">最低剩餘車位（滿位）</div>
        <div class="metric-value rose">{min_available:.0f}</div>
        <div class="metric-sub">{min_time}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card amber">
        <div class="metric-label">尖峰時段</div>
        <div class="metric-value amber">{peak_hours_str}</div>
        <div class="metric-sub">使用率 > 80%</div>
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

# ===== 趨勢圖處理 =====
granularity_map = {"5 分鐘": "5min", "15 分鐘": "15min", "30 分鐘": "30min", "1 小時": "1h", "4 小時": "4h"}
gran = granularity_map[time_granularity]
df['taipei_time'] = pd.to_datetime(df['taipei_time'])
trend_df = df.set_index('taipei_time').resample(gran).agg({'available_cars': 'mean', 'usage_rate': 'mean'}).reset_index()
trend_df.columns = ['time', 'available', 'usage_rate']

# ===== 主圖表：趨勢圖 =====
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
        line=dict(color='#22d3ee', width=3),
        fillcolor='rgba(34, 211, 238, 0.1)',
        name='剩餘車位'
    ))
    y_range = [0, total_cars * 1.1]
    y_title = '剩餘車位'
else:
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(
        x=trend_df['time'],
        y=trend_df['usage_rate'],
        mode='lines',
        fill='tozeroy',
        line=dict(color='#22d3ee', width=3),
        fillcolor='rgba(34, 211, 238, 0.1)',
        name='使用率'
    ))
    y_range = [0, 105]
    y_title = '使用率 (%)'

# [修改]: 更新字體顏色與大小
fig_main.update_layout(
    paper_bgcolor='#1e293b',
    plot_bgcolor='#1e293b',
    font=dict(color='#e2e8f0', size=14),
    margin=dict(l=40, r=40, t=40, b=40),
    height=450,
    yaxis_title=y_title,
    xaxis_title='時間',
    xaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)', zerolinecolor='rgba(51, 65, 85, 0.5)'),
    yaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)', zerolinecolor='rgba(51, 65, 85, 0.5)', range=y_range),
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
    # [修改]: 移除 cornerradius 參數以修復錯誤
    fig_hourly.add_trace(go.Bar(
        x=hourly_df['hour'],
        y=hourly_df['usage_rate'],
        marker=dict(color='#22d3ee'),
        name='使用率'
    ))
    fig_hourly.update_layout(
        paper_bgcolor='#1e293b',
        plot_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', size=14),
        margin=dict(l=40, r=40, t=40, b=40),
        height=380,
        yaxis_title='平均使用率 (%)',
        xaxis_title='小時',
        xaxis=dict(tickmode='linear', tick0=0, dtick=2, gridcolor='rgba(51, 65, 85, 0.5)'),
        yaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)', range=[0, 100])
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
    daily_df['label'] = daily_df.apply(lambda x: f"{x['date_str'][5:]} ({day_names[int(x['day_of_week'])]})", axis=1)
    
    colors = ['#a78bfa' if w else '#22d3ee' for w in daily_df['is_weekend']]
    
    fig_daily = go.Figure()
    # [修改]: 移除 cornerradius 參數以修復錯誤
    fig_daily.add_trace(go.Bar(
        x=daily_df['label'],
        y=daily_df['usage_rate'],
        marker=dict(color=colors),
        name='使用率'
    ))
    fig_daily.update_layout(
        paper_bgcolor='#1e293b',
        plot_bgcolor='#1e293b',
        font=dict(color='#e2e8f0', size=14),
        margin=dict(l=40, r=40, t=40, b=40),
        height=380,
        yaxis_title='平均使用率 (%)',
        xaxis_title='日期',
        xaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)', tickangle=-45),
        yaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)', range=[0, 100])
    )
    st.plotly_chart(fig_daily, use_container_width=True)

# ===== 熱力圖 (重點修改區) =====
st.markdown("""
<div class="chart-card">
    <div class="chart-title">使用率熱力圖（按日期×時段）</div>
</div>
""", unsafe_allow_html=True)

heatmap_data = df.groupby(['date_str', 'hour']).agg({'usage_rate': 'mean'}).reset_index()
heatmap_pivot = heatmap_data.pivot(index='date_str', columns='hour', values='usage_rate')

# [修改]: 重新定義顏色級距，針對高使用率停車場優化
# 舊版: >65% 就是紅色，導致全紅
# 新版: 拉開高使用率的層次，90%以上才紅，95%以上紫紅
custom_colorscale = [
    [0.0, '#10b981'],    # 0-60%  綠色 (舒適)
    [0.6, '#10b981'],
    [0.6, '#eab308'],    # 60-80% 黃色 (普通)
    [0.8, '#eab308'],
    [0.8, '#f97316'],    # 80-90% 橙色 (繁忙)
    [0.9, '#f97316'],
    [0.9, '#ef4444'],    # 90-95% 紅色 (擁擠)
    [0.95, '#ef4444'],
    [0.95, '#7f1d1d'],   # 95%+   深紅紫 (滿位/需排隊)
    [1.0, '#7f1d1d']
]

fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_pivot.values,
    x=heatmap_pivot.columns,
    y=heatmap_pivot.index,
    colorscale=custom_colorscale,
    zmin=0,
    zmax=100,
    colorbar=dict(title='使用率 (%)', titleside='right', tickfont=dict(color='#e2e8f0')),
    hovertemplate='日期: %{y}<br>時段: %{x}:00<br>使用率: %{z:.1f}%<extra></extra>'
))

fig_heatmap.update_layout(
    paper_bgcolor='#1e293b',
    plot_bgcolor='#1e293b',
    font=dict(color='#e2e8f0', size=14),
    margin=dict(l=40, r=40, t=40, b=40),
    height=max(300, len(heatmap_pivot) * 35), # 稍微增加每行高度
    xaxis_title='小時',
    yaxis_title='日期',
    xaxis=dict(tickmode='linear', tick0=0, dtick=1, gridcolor='rgba(51, 65, 85, 0.5)'),
    yaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)', autorange='reversed')
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# [修改]: 更新圖例說明以配合新的顏色級距
st.markdown("""
<div class="legend-container">
    <div class="legend-item">
        <div class="legend-color" style="background: #10b981;"></div>
        <span>舒適 (<60%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #eab308;"></div>
        <span>普通 (60-80%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #f97316;"></div>
        <span>繁忙 (80-90%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #ef4444;"></div>
        <span>擁擠 (90-95%)</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background: #7f1d1d;"></div>
        <span>滿位 (>95%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ===== 週間 vs 週末曲線 =====
st.markdown("""
<div class="chart-card">
    <div class="chart-title">週間 vs 週末 24小時使用率曲線</div>
</div>
""", unsafe_allow_html=True)

weekday_hourly = df[~df['is_weekend']].groupby('hour')['usage_rate'].mean().reset_index()
weekend_hourly = df[df['is_weekend']].groupby('hour')['usage_rate'].mean().reset_index()

fig_ww = go.Figure()
if not weekday_hourly.empty:
    fig_ww.add_trace(go.Scatter(
        x=weekday_hourly['hour'],
        y=weekday_hourly['usage_rate'],
        mode='lines',
        fill='tozeroy',
        line=dict(color='#22d3ee', width=3),
        fillcolor='rgba(34, 211, 238, 0.1)',
        name='週間平均'
    ))
if not weekend_hourly.empty:
    fig_ww.add_trace(go.Scatter(
        x=weekend_hourly['hour'],
        y=weekend_hourly['usage_rate'],
        mode='lines',
        fill='tozeroy',
        line=dict(color='#a78bfa', width=3),
        fillcolor='rgba(167, 139, 250, 0.1)',
        name='週末平均'
    ))

fig_ww.update_layout(
    paper_bgcolor='#1e293b',
    plot_bgcolor='#1e293b',
    font=dict(color='#e2e8f0', size=14),
    margin=dict(l=40, r=40, t=40, b=40),
    height=380,
    xaxis_title='小時',
    yaxis_title='使用率 (%)',
    xaxis=dict(tickmode='linear', tick0=0, dtick=2, gridcolor='rgba(51, 65, 85, 0.5)'),
    yaxis=dict(gridcolor='rgba(51, 65, 85, 0.5)', range=[0, 100]),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(color='#e2e8f0')),
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
