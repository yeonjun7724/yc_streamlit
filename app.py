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
import seaborn as sns
import numpy as np

# ───────────── 한글 깨짐 방지 ─────────────
matplotlib.rc('font', family='Malgun Gothic')  # 윈도우용
matplotlib.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

# ───────────── 페이지 기본 설정 ─────────────
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

# ───────────── 지도 데이터 ─────────────
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
COMMON_TILE = "CartoDB positron"
palette = ["#1f77b4", "#ff7f0e", "#2ca02c"]

ASIS_PATH = "cb_tobe_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

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
            res = requests.get(url, params=params).json()
            routes = res.get("routes") or []

            if routes:
                current_total_duration_sec += routes[0]["duration"]
                current_total_distance_km += routes[0]["distance"] / 1000
                coords = routes[0]["geometry"]["coordinates"]
                line = LineString(coords)
                style = {"color": color, "weight": 5}
                GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        current_cols[0].markdown(f"""
            <div style='text-align:center;'>현재 소요시간<br>
            <span style='font-size:32px;'>{int(current_total_duration_sec // 60)} 분</span></div>
        """, unsafe_allow_html=True)
        current_cols[1].markdown(f"""
            <div style='text-align:center;'>현재 최단거리<br>
            <span style='font-size:32px;'>{round(current_total_distance_km, 2)} km</span></div>
        """, unsafe_allow_html=True)
        current_cols[2].markdown(f"""
            <div style='text-align:center;'>현재 물류비<br>
            <span style='font-size:32px;'>{int(current_total_distance_km*5000):,} 원</span></div>
        """, unsafe_allow_html=True)
        current_cols[3].markdown(f"""
            <div style='text-align:center;'>현재 탄소배출량<br>
            <span style='font-size:32px;'>{round(current_total_distance_km*0.65, 2)} kg CO2</span></div>
        """, unsafe_allow_html=True)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[현재 에러] {e}")

# ───────────── 다타소(DaTaSo) 도입 후 ─────────────
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
                line = LineString(coords)
                style = {"color": palette[i % len(palette)], "weight": 5}
                GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        diff_duration = int((current_total_duration_sec - dataso_total_duration_sec) // 60)
        diff_distance = round(current_total_distance_km - dataso_total_distance_km, 2)
        diff_cost     = int((current_total_distance_km * 5000) - (dataso_total_distance_km * 5000))
        diff_emission = round((current_total_distance_km * 0.65) - (dataso_total_distance_km * 0.65), 2)

        dataso_cols[0].markdown(f"""
            <div style='text-align:center;'>다타소(DaTaSo) 이용 시 소요시간<br>
            <span style='font-size:32px;'>{int(dataso_total_duration_sec // 60)} 분</span><br>
            <span style='color:red;'>- {diff_duration} 분</span></div>
        """, unsafe_allow_html=True)
        dataso_cols[1].markdown(f"""
            <div style='text-align:center;'>다타소(DaTaSo) 이용 시 최단거리<br>
            <span style='font-size:32px;'>{round(dataso_total_distance_km, 2)} km</span><br>
            <span style='color:red;'>- {diff_distance} km</span></div>
        """, unsafe_allow_html=True)
        dataso_cols[2].markdown(f"""
            <div style='text-align:center;'>다타소(DaTaSo) 이용 시 물류비<br>
            <span style='font-size:32px;'>{int(dataso_total_distance_km*5000):,} 원</span><br>
            <span style='color:red;'>- {diff_cost:,} 원</span></div>
        """, unsafe_allow_html=True)
        dataso_cols[3].markdown(f"""
            <div style='text-align:center;'>다타소(DaTaSo) 이용 시 탄소배출량<br>
            <span style='font-size:32px;'>{round(dataso_total_distance_km*0.65, 2)} kg CO₂</span><br>
            <span style='color:red;'>- {diff_emission} kg CO₂</span></div>
        """, unsafe_allow_html=True)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[다타소 에러] {e}")
# ───────────── 정책 + 샘플 그래프 ─────────────
st.markdown("---")
st.markdown("### ✅ 정책별 샘플 그래프")

months = np.arange(1, 13)

# ✅ 2줄 3열 그리드
gcol1, gcol2, gcol3 = st.columns(3)

with gcol1:
    st.markdown("#### ✅ 계절성 분석")
    fig1, ax1 = plt.subplots(figsize=(5,4))
    sns.lineplot(x=months, y=50 + 20 * np.sin(np.linspace(0, 2*np.pi, 12)) + np.random.normal(0, 3, 12), marker='o', ax=ax1)
    ax1.set_title("월별 운송량 패턴")
    st.pyplot(fig1)

    st.markdown("#### ✅ 농촌 상생")
    fig2, ax2 = plt.subplots(figsize=(5,4))
    sns.barplot(x=['농가 A', '농가 B', '농가 C'], y=[100, 120, 80], palette="pastel", ax=ax2)
    ax2.set_title("농가별 소득 비교")
    st.pyplot(fig2)

with gcol2:
    st.markdown("#### ✅ 축산업 혁신")
    data = np.random.rand(5, 5)
    fig3, ax3 = plt.subplots(figsize=(5,4))
    sns.heatmap(data, annot=True, fmt=".2f", cmap="Blues", ax=ax3)
    ax3.set_title("스마트팜 센서 상관 Heatmap")
    st.pyplot(fig3)

    st.markdown("#### ✅ 지역별 특성")
    region_data = [
        np.random.normal(100, 15, 50),
        np.random.normal(120, 20, 50),
        np.random.normal(90, 10, 50)
    ]
    fig4, ax4 = plt.subplots(figsize=(5,4))
    ax4.boxplot(region_data, labels=['권역 A', '권역 B', '권역 C'])
    ax4.set_title("권역별 운송량 분포")
    st.pyplot(fig4)

with gcol3:
    st.markdown("#### ✅ 탄소배출 계산")
    fig5, ax5 = plt.subplots(figsize=(5,4))
    ax5.pie([30, 40, 30], labels=['운송', '사료', '기타'], autopct='%1.1f%%', startangle=140)
    ax5.set_title("배출원 비중 파이차트")
    st.pyplot(fig5)

    st.markdown("#### ✅ 시장 동향")
    fig6, ax6 = plt.subplots(figsize=(5,4))
    price = np.random.uniform(1000, 5000, 50)
    vol = 50 + 0.02 * price + np.random.normal(0, 5, 50)
    ax6.scatter(price, vol)
    ax6.set_title("가격 vs 운송량 산점도")
    ax6.set_xlabel("가격")
    ax6.set_ylabel("운송량")
    st.pyplot(fig6)
