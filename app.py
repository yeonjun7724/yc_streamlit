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
import matplotlib
import numpy as np

# ───────────── 한글 깨짐 방지 ─────────────
matplotlib.rc("font", family="Malgun Gothic")  # Windows. Mac은 'AppleGothic'
matplotlib.rc("axes", unicode_minus=False)

# ───────────── 와이드 레이아웃 ─────────────
st.set_page_config(layout="wide")

# ───────────── 로고 + 제목 ─────────────
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

# ───────────── 상수 ─────────────
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
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

st.markdown("---")

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

params = {
    "geometries": "geojson",
    "overview": "full",
    "steps": "true",
    "access_token": MAPBOX_TOKEN
}

col1, col2 = st.columns(2, gap="large")

# ───────────── 현재 경로 ─────────────
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
                line = LineString(routes[0]["geometry"]["coordinates"])
                style = {"color": color, "weight": 5}
            else:
                line = LineString([(c.x, c.y), (d.x, d.y)])
                style = {"color": color, "weight": 3, "dashArray": "5,5"}

            GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        # ✅ 현재 KPI
        current_cols[0].markdown(f"<div style='text-align:center;'>현재 소요시간<br><b>{int(current_total_duration_sec // 60)}분</b></div>", unsafe_allow_html=True)
        current_cols[1].markdown(f"<div style='text-align:center;'>현재 최단거리<br><b>{round(current_total_distance_km, 2)} km</b></div>", unsafe_allow_html=True)
        current_cols[2].markdown(f"<div style='text-align:center;'>현재 물류비<br><b>{int(current_total_distance_km*5000):,} 원</b></div>", unsafe_allow_html=True)
        current_cols[3].markdown(f"<div style='text-align:center;'>현재 탄소배출량<br><b>{round(current_total_distance_km*0.65, 2)} kg CO₂</b></div>", unsafe_allow_html=True)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[현재 에러] {e}")

# ───────────── 다타소 경로: stop_seq 기반 순차 연결 ─────────────
with col2:
    st.markdown("#### 다타소(DaTaSo) 도입 후")
    try:
        m = Map(location=[dataso_grp.geometry.y.mean(), dataso_grp.geometry.x.mean()],
                zoom_start=10, tiles=COMMON_TILE)
        fg = FeatureGroup(name="다타소")

        c_pts = dataso_grp[dataso_grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
        d_pt = dataso_grp[dataso_grp["location_t"] == "D"].geometry.iloc[0]

        dataso_total_duration_sec, dataso_total_distance_km = 0, 0

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
                line = LineString(coords)
                style = {"color": palette[i % len(palette)], "weight": 5}
                GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        diff_duration = int((current_total_duration_sec - dataso_total_duration_sec) // 60)
        diff_distance = round(current_total_distance_km - dataso_total_distance_km, 2)
        diff_cost = int((current_total_distance_km * 5000) - (dataso_total_distance_km * 5000))
        diff_emission = round((current_total_distance_km * 0.65) - (dataso_total_distance_km * 0.65), 2)

        dataso_cols[0].markdown(f"<div style='text-align:center;'>다타소 소요시간<br><b>{int(dataso_total_duration_sec // 60)}분</b><br><span style='color:red;'>↓ {diff_duration} 분</span></div>", unsafe_allow_html=True)
        dataso_cols[1].markdown(f"<div style='text-align:center;'>다타소 최단거리<br><b>{round(dataso_total_distance_km, 2)} km</b><br><span style='color:red;'>↓ {diff_distance} km</span></div>", unsafe_allow_html=True)
        dataso_cols[2].markdown(f"<div style='text-align:center;'>다타소 물류비<br><b>{int(dataso_total_distance_km*5000):,} 원</b><br><span style='color:red;'>↓ {diff_cost:,} 원</span></div>", unsafe_allow_html=True)
        dataso_cols[3].markdown(f"<div style='text-align:center;'>다타소 탄소배출량<br><b>{round(dataso_total_distance_km*0.65,2)} kg CO₂</b><br><span style='color:red;'>↓ {diff_emission} kg</span></div>", unsafe_allow_html=True)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[다타소 에러] {e}")

# ───────────── 정책 7개 카드형 + 샘플 그래프 ─────────────
st.markdown("---")
st.markdown("### 📌 정책·활용방안 + 분석 인사이트")

months = np.arange(1, 13)
volumes = np.random.randint(50, 150, size=12)
prices = np.random.uniform(1000, 5000, 30)
vols = np.random.uniform(40, 160, 30)

regions = ['권역 A', '권역 B', '권역 C']
data = [np.random.normal(100, 15, 50), np.random.normal(120, 20, 50), np.random.normal(90, 10, 50)]

farmers = ['농가 A', '농가 B', '농가 C']
income = np.random.randint(5, 15, size=3)

col1, col2, col3 = st.columns(3)

with col1:
    st.write("✅ 계절성 분석")
    fig1, ax1 = plt.subplots(figsize=(4,2.5))
    ax1.plot(months, volumes, marker='o')
    ax1.set_title("월별 운송량")
    st.pyplot(fig1)

    st.write("✅ 실시간 교통정보")
    fig4, ax4 = plt.subplots(figsize=(4,2.5))
    ax4.plot(months, np.random.randint(60, 180, size=12))
    ax4.set_title("도로 혼잡도 시계열")
    st.pyplot(fig4)

with col2:
    st.write("✅ 농촌 상생")
    fig2, ax2 = plt.subplots(figsize=(4,2.5))
    ax2.bar(farmers, income)
    ax2.set_title("농가 소득 증대")
    st.pyplot(fig2)

    st.write("✅ 지역별 특성")
    fig5, ax5 = plt.subplots(figsize=(4,2.5))
    ax5.boxplot(data, labels=regions)
    ax5.set_title("권역별 수요 변동성")
    st.pyplot(fig5)

with col3:
    st.write("✅ 시장 동향")
    fig3, ax3 = plt.subplots(figsize=(4,2.5))
    ax3.scatter(prices, vols)
    ax3.set_title("가격 vs 운송량")
    st.pyplot(fig3)

    st.write("✅ 탄소배출 계산")
    fig6, ax6 = plt.subplots(figsize=(4,2.5))
    ax6.plot(months, np.random.randint(10, 30, size=12))
    ax6.set_title("월별 탄소배출량")
    st.pyplot(fig6)

    st.write("✅ 축산업 혁신")
    fig7, ax7 = plt.subplots(figsize=(4,2.5))
    ax7.plot(months, np.random.randint(70, 200, size=12))
    ax7.set_title("스마트팜 데이터 흐름")
    st.pyplot(fig7)
