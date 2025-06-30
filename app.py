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
matplotlib.rcParams['font.family'] = 'Malgun Gothic'
matplotlib.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

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

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

params = {
    "geometries": "geojson",
    "overview": "full",
    "steps": "true",
    "access_token": MAPBOX_TOKEN
}

col1, col2 = st.columns(2, gap="large")

# ───────────── 슬림 범례 ─────────────
legend_html = """
 <div style="
 position: fixed; 
 top: 20px; right: 20px; width: 90px; height: auto; 
 background: rgba(255, 255, 255, 0.95);
 border-radius: 5px; 
 box-shadow: 0 2px 6px rgba(0,0,0,0.1); 
 z-index: 9999; 
 font-size: 12px; 
 padding: 6px 8px; 
 line-height: 1.4;">
 <div style="display: flex; align-items: center; margin-bottom: 4px;">
   <span style="background: #1f77b4; width: 10px; height: 10px; display: inline-block; margin-right: 4px; border-radius: 2px;"></span> 농가 1
 </div>
 <div style="display: flex; align-items: center; margin-bottom: 4px;">
   <span style="background: #ff7f0e; width: 10px; height: 10px; display: inline-block; margin-right: 4px; border-radius: 2px;"></span> 농가 2
 </div>
 <div style="display: flex; align-items: center; margin-bottom: 4px;">
   <span style="background: #2ca02c; width: 10px; height: 10px; display: inline-block; margin-right: 4px; border-radius: 2px;"></span> 농가 3
 </div>
 <div style="display: flex; align-items: center;">
   <i class="fa fa-flag-checkered" style="color:red; margin-right: 4px;"></i> 도축장
 </div>
 </div>
"""

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
                html=f'<div style="font-size:13px; color:#fff; background:{color}; border-radius:50%; width:28px; height:28px; text-align:center; line-height:28px;">{idx+1}</div>'
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

        fg.add_to(m)
        m.get_root().html.add_child(folium.Element(legend_html))

        current_cols[0].metric("현재 소요시간", f"{int(current_total_duration_sec // 60)} 분")
        current_cols[1].metric("현재 최단거리", f"{round(current_total_distance_km, 2)} km")
        current_cols[2].metric("현재 물류비", f"{int(current_total_distance_km*5000):,} 원")
        current_cols[3].metric("현재 탄소배출량", f"{round(current_total_distance_km*0.65, 2)} kg CO₂")

        render_map(m)
    except Exception as e:
        st.error(f"[현재 에러] {e}")

# ───────────── DaTaSo 도입 후 ─────────────
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
                html=f'<div style="font-size:13px; color:#fff; background:{palette[i % len(palette)]}; border-radius:50%; width:28px; height:28px; text-align:center; line-height:28px;">{i+1}</div>'
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

        fg.add_to(m)
        m.get_root().html.add_child(folium.Element(legend_html))

        diff_duration = int((current_total_duration_sec - dataso_total_duration_sec) // 60)
        diff_distance = round(current_total_distance_km - dataso_total_distance_km, 2)
        diff_cost = int((current_total_distance_km * 5000) - (dataso_total_distance_km * 5000))
        diff_emission = round((current_total_distance_km * 0.65) - (dataso_total_distance_km * 0.65), 2)

        dataso_cols[0].metric("다타소(DaTaSo) 소요시간", f"{int(dataso_total_duration_sec // 60)} 분", f"-{diff_duration} 분")
        dataso_cols[1].metric("다타소(DaTaSo) 최단거리", f"{round(dataso_total_distance_km, 2)} km", f"-{diff_distance} km")
        dataso_cols[2].metric("다타소(DaTaSo) 물류비", f"{int(dataso_total_distance_km*5000):,} 원", f"-{diff_cost:,} 원")
        dataso_cols[3].metric("다타소(DaTaSo) 탄소배출량", f"{round(dataso_total_distance_km*0.65, 2)} kg CO₂", f"-{diff_emission} kg CO₂")

        render_map(m)
    except Exception as e:
        st.error(f"[다타소 에러] {e}")

# ───────────── 정책 그래프 ─────────────
st.markdown("---")
st.markdown("### 📊 정책별 샘플 그래프")

col1, col2, col3 = st.columns(3)
months = np.arange(1, 13)

with col1:
    st.markdown("### ✅ 계절성 분석")
    fig1, ax1 = plt.subplots(figsize=(5, 4))
    sns.lineplot(x=months, y=50 + 20 * np.sin(np.linspace(0, 2*np.pi, 12)), marker='o', ax=ax1)
    st.pyplot(fig1)

    st.markdown("### ✅ 농촌 상생")
    fig2, ax2 = plt.subplots(figsize=(5, 4))
    sns.barplot(x=['농가 A', '농가 B', '농가 C'], y=[100, 120, 80], palette="pastel", ax=ax2)
    st.pyplot(fig2)

with col2:
    st.markdown("### ✅ 축산업 혁신")
    fig3, ax3 = plt.subplots(figsize=(5, 4))
    sns.heatmap(np.random.rand(5, 5), annot=True, fmt=".2f", cmap="Blues", ax=ax3)
    st.pyplot(fig3)

    st.markdown("### ✅ 지역별 특성")
    fig4, ax4 = plt.subplots(figsize=(5, 4))
    ax4.boxplot([np.random.normal(100, 15, 50), np.random.normal(120, 20, 50), np.random.normal(90, 10, 50)], labels=['권역 A', '권역 B', '권역 C'])
    st.pyplot(fig4)

with col3:
    st.markdown("### ✅ 탄소배출 계산")
    fig5, ax5 = plt.subplots(figsize=(5, 4))
    ax5.pie([30, 40, 30], labels=['운송', '사료', '기타'], autopct='%1.1f%%')
    st.pyplot(fig5)

    st.markdown("### ✅ 시장 동향")
    fig6, ax6 = plt.subplots(figsize=(5, 4))
    price = np.random.uniform(1000, 5000, 50)
    vol = 50 + 0.02 * price + np.random.normal(0, 5, 50)
    ax6.scatter(price, vol)
    st.pyplot(fig6)
