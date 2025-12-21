import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta

# ===== 頁面設定 =====
st.set_page_config(
    page_title="台北停車場分析儀表板",
    page_icon="🚗",
    layout="wide"
)

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
    SELECT id, name, area, total_cars, total_motor
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

# ===== 頁面標題 =====
st.title("🚗 台北停車場分析儀表板")

# ===== 側邊欄：篩選條件 =====
st.sidebar.header("篩選條件")

# 取得停車場清單
parking_lots = get_parking_lots()

# 停車場選擇器
selected_lot_name = st.sidebar.selectbox(
    "選擇停車場",
    parking_lots['name'].tolist(),
    index=parking_lots[parking_lots['id'] == 'TPE0410'].index[0] if 'TPE0410' in parking_lots['id'].values else 0
)

# 取得選中停車場的資訊
selected_lot = parking_lots[parking_lots['name'] == selected_lot_name].iloc[0]
parking_lot_id = selected_lot['id']
total_cars = int(selected_lot['total_cars'])

# 顯示停車場資訊
st.sidebar.info(f"""
**停車場 ID**: {parking_lot_id}  
**汽車總車位**: {total_cars}  
**機車總車位**: {int(selected_lot['total_motor'])}  
**行政區**: {selected_lot['area']}
""")

# 日期範圍選擇器
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "開始日期",
        datetime.now() - timedelta(days=7)
    )
with col2:
    end_date = st.date_input(
        "結束日期",
        datetime.now()
    )

# 時間粒度選擇器
time_granularity = st.sidebar.radio(
    "時間粒度",
    ["5 分鐘", "每小時", "每日"],
    index=1
)

# ===== 讀取資料 =====
with st.spinner('載入資料中...'):
    df = get_parking_data(parking_lot_id, start_date, end_date, total_cars)

if df.empty:
    st.warning("所選日期範圍內沒有資料，請調整日期範圍。")
    st.stop()

# ===== 關鍵指標卡片 =====
st.subheader(f"📊 {selected_lot_name} - 關鍵指標")

col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_usage = df['usage_rate'].mean()
    st.metric("平均使用率", f"{avg_usage:.1f}%")

with col2:
    max_usage = df['usage_rate'].max()
    st.metric("最高使用率", f"{max_usage:.1f}%")

with col3:
    min_usage = df['usage_rate'].min()
    st.metric("最低使用率", f"{min_usage:.1f}%")

with col4:
    st.metric("汽車總車位", f"{total_cars}")

# ===== 使用率趨勢圖 =====
st.subheader("📈 使用率趨勢")

# 根據時間粒度聚合資料
if time_granularity == "5 分鐘":
    trend_df = df.copy()
    trend_df['time'] = pd.to_datetime(trend_df['taipei_time'])
elif time_granularity == "每小時":
    df['hour_bucket'] = pd.to_datetime(df['taipei_time']).dt.floor('H')
    trend_df = df.groupby('hour_bucket').agg({'usage_rate': 'mean'}).reset_index()
    trend_df.columns = ['time', 'usage_rate']
else:  # 每日
    trend_df = df.groupby('date_str').agg({'usage_rate': 'mean'}).reset_index()
    trend_df.columns = ['time', 'usage_rate']
    trend_df['time'] = pd.to_datetime(trend_df['time'])

fig_trend = px.line(
    trend_df, 
    x='time', 
    y='usage_rate',
    labels={'time': '時間', 'usage_rate': '使用率 (%)'},
)
fig_trend.update_layout(
    yaxis_range=[0, 105],
    hovermode='x unified'
)
fig_trend.update_traces(line_color='#1f77b4')

st.plotly_chart(fig_trend, use_container_width=True)

# ===== 每小時平均使用率 =====
st.subheader("🕐 每小時平均使用率")

hourly_df = df.groupby('hour').agg({'usage_rate': 'mean'}).reset_index()
hourly_df.columns = ['hour', 'avg_usage_rate']

fig_hourly = px.bar(
    hourly_df,
    x='hour',
    y='avg_usage_rate',
    labels={'hour': '小時', 'avg_usage_rate': '平均使用率 (%)'},
)
fig_hourly.update_layout(
    yaxis_range=[0, 105],
    xaxis=dict(tickmode='linear', tick0=0, dtick=1)
)
fig_hourly.update_traces(marker_color='#2ecc71')

st.plotly_chart(fig_hourly, use_container_width=True)

# ===== 熱力圖：星期幾 × 小時 =====
st.subheader("🗓️ 使用率熱力圖（星期 × 小時）")

# 建立熱力圖資料
heatmap_df = df.groupby(['day_of_week', 'hour']).agg({'usage_rate': 'mean'}).reset_index()
heatmap_pivot = heatmap_df.pivot(index='day_of_week', columns='hour', values='usage_rate')

# 星期幾標籤（BigQuery DAYOFWEEK: 1=Sunday, 2=Monday, ..., 7=Saturday）
day_labels = ['日', '一', '二', '三', '四', '五', '六']

fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_pivot.values,
    x=heatmap_pivot.columns,
    y=[day_labels[int(d)-1] for d in heatmap_pivot.index],
    colorscale='RdYlGn_r',
    zmin=0,
    zmax=100,
    colorbar=dict(title='使用率 (%)')
))

fig_heatmap.update_layout(
    xaxis_title='小時',
    yaxis_title='星期',
    xaxis=dict(tickmode='linear', tick0=0, dtick=1)
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# ===== 頁尾 =====
st.markdown("---")
st.markdown(
    f"資料更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    f"資料範圍：{start_date} 至 {end_date}"
)
