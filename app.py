import streamlit as st
import geopandas as gpd
import requests
import base64
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, GeoJson
from folium.features import DivIcon
from streamlit.components.v1 import html

# ───────────── 와이드 레이아웃 ─────────────
st.set_page_config(layout="wide")

# ───────────── Base64 이미지 인코딩 ─────────────
file_path = "./image.jpg"
with open(file_path, "rb") as f:
    img_bytes = f.read()
encoded = base64.b64encode(img_bytes).decode()

# ───────────── 상단 로고 + 제목 ─────────────
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

# ───────────── 데이터 로드 ─────────────
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

        # ✅ 현재 KPI 출력 (다타소와 동일 스타일)
        current_cols[0].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>현재 소요시간</div>
                <div style='font-size:32px; font-weight:bold;'>{int(current_total_duration_sec // 60)} <span style='font-size:18px;'>분</span></div>
            </div>
        """, unsafe_allow_html=True)

        current_cols[1].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>현재 최단거리</div>
                <div style='font-size:32px; font-weight:bold;'>{round(current_total_distance_km, 2)} <span style='font-size:18px;'>km</span></div>
            </div>
        """, unsafe_allow_html=True)

        current_cols[2].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>현재 물류비</div>
                <div style='font-size:32px; font-weight:bold;'>{int(current_total_distance_km*5000):,} <span style='font-size:18px;'>원</span></div>
            </div>
        """, unsafe_allow_html=True)

        current_cols[3].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>현재 탄소배출량</div>
                <div style='font-size:32px; font-weight:bold;'>{round(current_total_distance_km*0.65, 2)} <span style='font-size:18px;'>kg CO2</span></div>
            </div>
        """, unsafe_allow_html=True)

        # ✅ 현재 지도 범례 (범례 타이틀 제거)
        legend_items = ""
        for idx in range(len(c_pts)):
            legend_items += f"""
                <div style="display:flex; align-items:center; margin-bottom:5px;">
                    <div style="width:20px;height:20px;background:{palette[idx % len(palette)]}; border-radius:50%; margin-right:6px;"></div>
                    농가 {idx+1}
                </div>
            """
        legend_html_current = f"""
        <div style="
            position: fixed; 
            top: 30px; right: 30px; 
            background-color: white; 
            border: 1px solid #ddd; 
            border-radius: 8px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
            padding: 10px 15px; 
            z-index:9999; 
            font-size: 13px;">
            {legend_items}
            <div style="display:flex; align-items:center; margin-top:5px;">
                <i class="fa fa-flag-checkered" style="color:red;margin-right:6px;"></i> 도축장
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html_current))

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
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 소요시간</div>
                <div style='font-size:32px; font-weight:bold;'>{int(dataso_total_duration_sec // 60)} <span style='font-size:18px;'>분</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>- {diff_duration} 분</div>
            </div>
        """, unsafe_allow_html=True)

        dataso_cols[1].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 최단거리</div>
                <div style='font-size:32px; font-weight:bold;'>{round(dataso_total_distance_km, 2)} <span style='font-size:18px;'>km</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>- {diff_distance} km</div>
            </div>
        """, unsafe_allow_html=True)

        dataso_cols[2].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 물류비</div>
                <div style='font-size:32px; font-weight:bold;'>{int(dataso_total_distance_km*5000):,} <span style='font-size:18px;'>원</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>- {diff_cost:,} 원</div>
            </div>
        """, unsafe_allow_html=True)

        dataso_cols[3].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 탄소배출량</div>
                <div style='font-size:32px; font-weight:bold;'>{round(dataso_total_distance_km*0.65,2)} <span style='font-size:18px;'>kg CO2</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>- {diff_emission} kg CO2</div>
            </div>
        """, unsafe_allow_html=True)

        legend_items = ""
        for idx in range(len(c_pts)):
            legend_items += f"""
                <div style="display:flex; align-items:center; margin-bottom:5px;">
                    <div style="width:20px;height:20px;background:{palette[idx % len(palette)]}; border-radius:50%; margin-right:6px;"></div>
                    농가 {idx+1}
                </div>
            """
        legend_html_dataso = f"""
        <div style="
            position: fixed; 
            top: 30px; right: 30px; 
            background-color: white; 
            border: 1px solid #ddd; 
            border-radius: 8px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
            padding: 10px 15px; 
            z-index:9999; 
            font-size: 13px;">
            {legend_items}
            <div style="display:flex; align-items:center; margin-top:5px;">
                <i class="fa fa-flag-checkered" style="color:red;margin-right:6px;"></i> 도축장
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html_dataso))

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[다타소 에러] {e}")

import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib

# ───────────── Font & Style ─────────────
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows: 맑은 고딕
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid")

st.markdown("---")
st.markdown("## 📊 Advanced Data Insights")

# ───────────── Random Seed ─────────────
np.random.seed(42)

# ───────────── Raw Data ─────────────
# 1) Farm Production
farmers = [f'Farm {chr(65+i)}' for i in range(6)]
production = np.random.randint(90, 160, size=6)

# 2) Region Indicator
zones = [f'Region {chr(65+i)}' for i in range(4)]
region_data = [np.random.normal(100+10*i, 8+2*i, 70) for i in range(4)]

# 3) Seasonal Index
months = np.arange(1,13)
seasonal = 60 + 18 * np.sin(np.linspace(0, 2*np.pi, 12)) + np.random.normal(0, 3, 12)
growth = np.diff(seasonal, prepend=seasonal[0])

# 4) Carbon Emission Ratio
carbon_labels = ['Transport', 'Feed', 'Energy', 'Facility', 'Waste', 'Other']
carbon_sizes = [30, 25, 20, 10, 10, 5]

# 5) Innovation Correlation
corr_matrix = np.round(np.random.uniform(0.1, 0.95, size=(6,6)), 2)

# 6) Price vs Volume
price = np.random.uniform(2000, 9000, 120)
volume = 35 + 0.02*price + np.random.normal(0, 5, 120)

# ───────────── Columns ─────────────
col1, col2, col3 = st.columns(3)

# ───────────── 1) Farm Production ─────────────
with col1:
    st.markdown("### ✅ Farm Production")
    fig, ax = plt.subplots(figsize=(4,3))
    sns.barplot(x=farmers, y=production, palette="pastel", ax=ax)
    mean_prod = np.mean(production)
    ax.axhline(mean_prod, ls='--', color='red', label='Mean')
    for i, v in enumerate(production):
        ax.text(i, v+2, f"{v} tons", ha='center', fontsize=7)
    ax.set_ylabel("Production (tons)", fontsize=9)
    ax.set_xlabel("Farm", fontsize=9)
    ax.set_title("Annual Production per Farm")
    ax.legend()
    st.pyplot(fig)

# ───────────── 2) Region Indicator ─────────────
with col2:
    st.markdown("### ✅ Regional Indicator")
    fig, ax = plt.subplots(figsize=(4,3))
    ax.boxplot(region_data, labels=zones, patch_artist=True,
               boxprops=dict(facecolor='#90be6d'),
               medianprops=dict(color='white'))
    means = [np.mean(z) for z in region_data]
    for i, m in enumerate(means):
        ax.text(i+1, m+2, f"{m:.1f}", ha='center', fontsize=7)
    ax.set_ylabel("Indicator Score", fontsize=9)
    ax.set_xlabel("Region", fontsize=9)
    ax.set_title("Distribution of Regional Indicators")
    st.pyplot(fig)

# ───────────── 3) Seasonal Index ─────────────
with col3:
    st.markdown("### ✅ Seasonal Index")
    fig, ax = plt.subplots(figsize=(4,3))
    sns.lineplot(x=months, y=seasonal, marker='o', color="#0077b6", ax=ax)
    for x, y, g in zip(months, seasonal, growth):
        ax.text(x, y+0.8, f"{y:.1f}", ha='center', fontsize=6)
        if x > 1:
            ax.annotate(f"{g:+.1f}", xy=(x,y), xytext=(x,y+3), fontsize=6)
    ax.set_xlabel("Month", fontsize=9)
    ax.set_ylabel("Seasonal Index", fontsize=9)
    ax.set_title("Monthly Seasonal Trend with Change")
    st.pyplot(fig)

# ───────────── 4) Carbon Emission Ratio ─────────────
with col1:
    st.markdown("### ✅ Carbon Emission Ratio")
    fig, ax = plt.subplots(figsize=(4,3))
    wedges, texts, autotexts = ax.pie(
        carbon_sizes, labels=carbon_labels, autopct='%1.1f%%',
        colors=sns.color_palette("pastel"), startangle=90,
        wedgeprops=dict(width=0.5, edgecolor='w'))
    ax.set_title("Proportion of Carbon Emission Sources")
    st.pyplot(fig)

# ───────────── 5) Innovation Correlation ─────────────
with col2:
    st.markdown("### ✅ Innovation Correlation")
    fig, ax = plt.subplots(figsize=(4,3))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="YlGnBu",
                linewidths=0.5, linecolor='grey',
                cbar_kws={'label': 'Correlation'}, ax=ax)
    ax.set_title("Correlation Between Innovation Factors")
    st.pyplot(fig)

# ───────────── 6) Price vs Volume ─────────────
with col3:
    st.markdown("### ✅ Price vs Volume")
    fig, ax = plt.subplots(figsize=(4,3))
    sns.scatterplot(x=price, y=volume, color="#023047", s=30, edgecolor='w', ax=ax)
    m, b = np.polyfit(price, volume, 1)
    ax.plot(price, m*price + b, color='red', linestyle='--', label='Trendline')
    ax.set_xlabel("Price (KRW/kg)", fontsize=9)
    ax.set_ylabel("Volume (tons)", fontsize=9)
    ax.set_title("Price vs Sales Volume with Trendline")
    ax.legend()
    st.pyplot(fig)

