# ───────────── 공통 라이브러리 ─────────────
import streamlit as st
import geopandas as gpd
import requests
import base64
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, GeoJson
from folium.features import DivIcon
from streamlit.components.v1 import html

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ───────────── 페이지 설정 ─────────────
st.set_page_config(layout="wide")

# ───────────── 상단 로고 + 제목 ─────────────
file_path = "./image.jpg"
with open(file_path, "rb") as f:
    img_bytes = f.read()
encoded = base64.b64encode(img_bytes).decode()

st.markdown(
    f"""
    <div style='display: flex; align-items: center; justify-content: center; margin-bottom: 15px;'>
        <img src="data:image/png;base64,{encoded}" style='width: 180px; margin-right: 20px;'/>
        <h2 style='margin: 0; color: #333; text-align: center;'>
            지속가능한 축산물류를 위한 탄소저감형 가축운송 플랫폼
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

# ───────────── Map 상수 ─────────────
MAPBOX_TOKEN = "pk.eyJ1IjoibmV3LXRva2VuLXZhbHVlIiwiYSI6ImNsa2Yzc2gwazA2eTQzZXFxajZ5ajQxdm8ifQ.REPLACE_ME"  # 본인 토큰으로 교체!
ASIS_PATH = "cb_tobe_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"
COMMON_TILE = "CartoDB positron"
palette = ["#1f77b4", "#ff7f0e", "#2ca02c"]

# ───────────── 데이터 ─────────────
gdf_current = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_dataso = gpd.read_file(TOBE_PATH).to_crs(4326)

common_ids = sorted(set(gdf_current["sorting_id"]) & set(gdf_dataso["sorting_id"]))
selected_id = st.selectbox("농가 선택", common_ids)

current_grp = gdf_current[gdf_current["sorting_id"] == selected_id]
dataso_grp = gdf_dataso[gdf_dataso["sorting_id"] == selected_id]

current_cols = st.columns(4)
dataso_cols = st.columns(4)

params = {
    "geometries": "geojson",
    "overview": "full",
    "steps": "true",
    "access_token": MAPBOX_TOKEN
}

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

col1, col2 = st.columns(2, gap="large")

# ───────────── ✅ 현재 경로 ─────────────
with col1:
    st.markdown("#### 현재")
    try:
        m = Map(location=[current_grp.geometry.y.mean(), current_grp.geometry.x.mean()],
                zoom_start=10, tiles=COMMON_TILE)
        fg = FeatureGroup(name="현재")

        c_pts = current_grp[current_grp["location_t"] == "C"].reset_index()
        d_pts = current_grp[current_grp["location_t"] == "D"].reset_index()

        current_total_duration_sec, current_total_distance_km = 0, 0

        for idx, crow in enumerate(c_pts.itertuples()):
            color = palette[idx % len(palette)]
            c = crow.geometry
            d = d_pts.loc[d_pts.geometry.distance(c).idxmin()].geometry

            folium.Marker([c.y, c.x], icon=DivIcon(
                icon_size=(30,30), icon_anchor=(15,15),
                html=f'<div style="font-size:14px; color:#fff; background:{color}; border-radius:50%; width:30px; height:30px; text-align:center; line-height:30px;">{idx+1}</div>'
            )).add_to(fg)

            folium.Marker([d.y, d.x], icon=folium.Icon(icon="flag-checkered", prefix="fa", color="red")).add_to(fg)

            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{c.x},{c.y};{d.x},{d.y}"
            res = requests.get(url, params=params)
            data = res.json()
            routes = data.get("routes") or []

            if routes:
                current_total_duration_sec += routes[0]["duration"]
                current_total_distance_km += routes[0]["distance"] / 1000
                coords = routes[0]["geometry"]["coordinates"]
                GeoJson(LineString(coords), style_function=lambda _, s={"color": color, "weight": 4}: s).add_to(fg)

        fg.add_to(m)
        render_map(m)

        current_cols[0].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>현재 소요시간</div><div style='font-size:32px; font-weight:bold;'>{int(current_total_duration_sec // 60)} 분</div></div>""", unsafe_allow_html=True)
        current_cols[1].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>현재 최단거리</div><div style='font-size:32px; font-weight:bold;'>{round(current_total_distance_km, 2)} km</div></div>""", unsafe_allow_html=True)
        current_cols[2].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>현재 물류비</div><div style='font-size:32px; font-weight:bold;'>{int(current_total_distance_km*5000):,} 원</div></div>""", unsafe_allow_html=True)
        current_cols[3].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>현재 탄소배출량</div><div style='font-size:32px; font-weight:bold;'>{round(current_total_distance_km*0.65, 2)} kg CO2</div></div>""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"[현재 에러] {e}")

# ───────────── ✅ 다타소(DaTaSo) 경로 ─────────────
with col2:
    st.markdown("#### 다타소(DaTaSo) 도입 후")
    try:
        m = Map(location=[dataso_grp.geometry.y.mean(), dataso_grp.geometry.x.mean()],
                zoom_start=10, tiles=COMMON_TILE)
        fg = FeatureGroup(name="다타소")

        c_pts = dataso_grp[dataso_grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
        d_pt = dataso_grp[dataso_grp["location_t"] == "D"].geometry.iloc[0]

        dataso_total_duration_sec, dataso_total_distance_km = 0, 0

        for i, row in c_pts.iterrows():
            folium.Marker([row.geometry.y, row.geometry.x], icon=DivIcon(
                icon_size=(30,30), icon_anchor=(15,15),
                html=f'<div style="font-size:14px; color:#fff; background:{palette[i % len(palette)]}; border-radius:50%; width:30px; height:30px; text-align:center; line-height:30px;">{i+1}</div>'
            )).add_to(fg)

        folium.Marker([d_pt.y, d_pt.x], icon=folium.Icon(icon="flag-checkered", prefix="fa", color="red")).add_to(fg)

        for i in range(len(c_pts)):
            start = c_pts.geometry.iloc[i]
            end = c_pts.geometry.iloc[i+1] if i < len(c_pts)-1 else d_pt

            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{start.x},{start.y};{end.x},{end.y}"
            res = requests.get(url, params=params).json()
            routes = res.get("routes") or []

            if routes:
                dataso_total_duration_sec += routes[0]["duration"]
                dataso_total_distance_km += routes[0]["distance"] / 1000
                coords = routes[0]["geometry"]["coordinates"]
                GeoJson(LineString(coords), style_function=lambda _, s={"color": palette[i % len(palette)], "weight": 4}: s).add_to(fg)

        fg.add_to(m)
        render_map(m)

        dataso_cols[0].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>다타소 소요시간</div><div style='font-size:32px; font-weight:bold;'>{int(dataso_total_duration_sec // 60)} 분</div></div>""", unsafe_allow_html=True)
        dataso_cols[1].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>다타소 최단거리</div><div style='font-size:32px; font-weight:bold;'>{round(dataso_total_distance_km, 2)} km</div></div>""", unsafe_allow_html=True)
        dataso_cols[2].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>다타소 물류비</div><div style='font-size:32px; font-weight:bold;'>{int(dataso_total_distance_km*5000):,} 원</div></div>""", unsafe_allow_html=True)
        dataso_cols[3].markdown(f"""<div style='text-align:center;'><div style='font-size:14px;'>다타소 탄소배출량</div><div style='font-size:32px; font-weight:bold;'>{round(dataso_total_distance_km*0.65, 2)} kg CO2</div></div>""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"[다타소 에러] {e}")

# ───────────── ✅ 구분선 ─────────────
st.markdown("---")
st.markdown("## 📊 Advanced Data Insights")

# ───────────── ✅ 논문형 그래프 ─────────────
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams.update({
    'axes.titlesize': 10, 'axes.labelsize': 8, 'xtick.labelsize': 7,
    'ytick.labelsize': 7, 'legend.fontsize': 7
})
sns.set_theme(style="whitegrid")
np.random.seed(42)

farmers = [f'Farm {chr(65+i)}' for i in range(6)]
production = np.random.randint(90, 160, size=6)
zones = [f'Region {chr(65+i)}' for i in range(4)]
region_data = [np.random.normal(100+10*i, 8+2*i, 70) for i in range(4)]
months = np.arange(1,13)
seasonal = 60 + 18 * np.sin(np.linspace(0, 2*np.pi, 12)) + np.random.normal(0, 3, 12)
corr_matrix = np.round(np.random.uniform(0.1, 0.95, size=(6,6)), 2)
price = np.random.uniform(2000, 9000, 120)
volume = 35 + 0.02*price + np.random.normal(0, 5, 120)
carbon_labels = ['Transport', 'Feed', 'Energy', 'Facility', 'Waste', 'Other']
carbon_sizes = [30, 25, 20, 10, 10, 5]

col1, _, col2, _, col3 = st.columns([1, 0.05, 1, 0.05, 1])

with col1:
    fig, ax = plt.subplots(figsize=(4,2.5))
    sns.barplot(x=farmers, y=production, palette="pastel", ax=ax)
    ax.set_title("Farm Production")
    st.pyplot(fig)

with col2:
    fig, ax = plt.subplots(figsize=(4,2.5))
    ax.boxplot(region_data, labels=zones)
    ax.set_title("Region Indicator")
    st.pyplot(fig)

with col3:
    fig, ax = plt.subplots(figsize=(4,2.5))
    sns.lineplot(x=months, y=seasonal, marker='o', ax=ax)
    ax.set_title("Seasonal Index")
    st.pyplot(fig)

with col1:
    fig, ax = plt.subplots(figsize=(4,2.5))
    wedges, _, _ = ax.pie(carbon_sizes, labels=carbon_labels, autopct='%1.1f%%')
    ax.set_title("Carbon Emission Ratio")
    st.pyplot(fig)

with col2:
    fig, ax = plt.subplots(figsize=(4,2.5))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="YlGnBu", ax=ax)
    ax.set_title("Innovation Correlation")
    st.pyplot(fig)

with col3:
    fig, ax = plt.subplots(figsize=(4,2.5))
    sns.scatterplot(x=price, y=volume, ax=ax)
    m, b = np.polyfit(price, volume, 1)
    ax.plot(price, m*price + b, color='red', linestyle='--')
    ax.set_title("Price vs Volume")
    st.pyplot(fig)
