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
        # ✅ 차이값
        diff_duration = int((current_total_duration_sec - dataso_total_duration_sec) // 60)
        diff_distance = round(current_total_distance_km - dataso_total_distance_km, 2)
        diff_cost = int((current_total_distance_km * 5000) - (dataso_total_distance_km * 5000))
        diff_emission = round((current_total_distance_km * 0.65) - (dataso_total_distance_km * 0.65), 2)
        
        # ✅ 퍼센트값 (분모가 0일 경우 대비)
        diff_duration_pct = round((diff_duration / (current_total_duration_sec // 60) * 100), 1) if current_total_duration_sec != 0 else 0
        diff_distance_pct = round((diff_distance / current_total_distance_km * 100), 1) if current_total_distance_km != 0 else 0
        diff_cost_pct = round((diff_cost / (current_total_distance_km * 5000) * 100), 1) if current_total_distance_km != 0 else 0
        diff_emission_pct = round((diff_emission / (current_total_distance_km * 0.65) * 100), 1) if current_total_distance_km != 0 else 0
        
        # ✅ 소요시간 KPI
        dataso_cols[0].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 소요시간</div>
                <div style='font-size:32px; font-weight:bold;'>{int(dataso_total_duration_sec // 60)} <span style='font-size:18px;'>분</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>
                    - {diff_duration} 분 <span style='margin-left:4px;'>({diff_duration_pct}%)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # ✅ 최단거리 KPI
        dataso_cols[1].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 최단거리</div>
                <div style='font-size:32px; font-weight:bold;'>{round(dataso_total_distance_km, 2)} <span style='font-size:18px;'>km</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>
                    - {diff_distance} km <span style='margin-left:4px;'>({diff_distance_pct}%)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # ✅ 물류비 KPI
        dataso_cols[2].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 물류비</div>
                <div style='font-size:32px; font-weight:bold;'>{int(dataso_total_distance_km*5000):,} <span style='font-size:18px;'>원</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>
                    - {diff_cost:,} 원 <span style='margin-left:4px;'>({diff_cost_pct}%)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # ✅ 탄소배출량 KPI
        dataso_cols[3].markdown(f"""
            <div style='text-align:center;'>
                <div style='font-size:14px; margin-bottom:4px;'>다타소(DaTaSo) 이용 시 탄소배출량</div>
                <div style='font-size:32px; font-weight:bold;'>{round(dataso_total_distance_km*0.65,2)} <span style='font-size:18px;'>kg CO2</span></div>
                <div style='font-size:14px; color:red; font-weight:bold; margin-top:4px;'>
                    - {diff_emission} kg CO2 <span style='margin-left:4px;'>({diff_emission_pct}%)</span>
                </div>
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

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

# ───────────── 전역 설정 ─────────────
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 6
sns.set_style("whitegrid")
np.random.seed(123)

# ───────────── Dummy Data ─────────────
months = np.tile(np.arange(1, 13), 50)
season_shipments = []
for m in range(1, 13):
    base = 100 + 30 * np.sin(2 * np.pi * m / 12)
    vals = base + np.random.normal(0, 5, 50)
    for v in vals:
        season_shipments.append({"Month": m, "Shipment": v})
df_season = pd.DataFrame(season_shipments)

farms = [f"Farm {chr(65+i)}" for i in range(10)]
farm_revenues = []
for farm in farms:
    for i in range(50):
        val = np.random.normal(50000, 5000) + np.random.uniform(-5000, 5000)
        farm_revenues.append({"Farm": farm, "Revenue": val})
df_farm = pd.DataFrame(farm_revenues)

df_heat = pd.DataFrame(
    np.round(np.random.rand(20, 20) * 100, 1),
    columns=[f"V{i+1}" for i in range(20)],
    index=[f"S{i+1}" for i in range(20)]
)

regions = ["Region A", "Region B", "Region C"]
region_production = []
for region in regions:
    for i in range(70):
        if region == "Region A":
            val = np.random.normal(150, 20)
        elif region == "Region B":
            val = np.random.normal(200, 30)
        else:
            val = np.random.normal(100, 15)
        region_production.append({"Region": region, "Production": val})
df_region = pd.DataFrame(region_production)

df_carbon = pd.DataFrame({
    "Category": ["Transport", "Feed", "Processing", "Waste", "Others"],
    "Ratio": [0.4, 0.25, 0.15, 0.1, 0.1]
})

prices = np.random.uniform(1000, 20000, 200)
volumes = 100 + 0.02 * prices + np.random.normal(0, 10, 200)
df_market = pd.DataFrame({"Price": prices, "Volume": volumes})

# ───────────── Streamlit Layout ─────────────
st.markdown("---")
st.markdown("#### 농가별 세부사항 분석")

# ───────────── 첫 번째 줄 ─────────────
row1 = st.columns(3, gap="large")

with row1[0]:
    st.markdown("##### 1) 농가별 특성: 농가별 운송 수요 변동성 예측")
    fig1, ax1 = plt.subplots(figsize=(6, 3.5))
    sns.boxplot(data=df_farm, x="Farm", y="Revenue",
                palette="Paired", ax=ax1)
    sns.stripplot(data=df_farm, x="Farm", y="Revenue",
                  color=".3", size=1.5, jitter=True, ax=ax1)
    ax1.set_xlabel("", fontsize=6)
    ax1.set_ylabel("Revenue ($)", fontsize=6)
    ax1.tick_params(axis='x', rotation=30, labelsize=6)
    ax1.tick_params(axis='y', labelsize=6)
    st.pyplot(fig1)

with row1[1]:
    st.markdown("##### 2) 지역별 특성: 권역별 운송 수요 변동성 예측")
    fig2, ax2 = plt.subplots(figsize=(4, 2.5))
    sns.boxplot(data=df_region, x="Region", y="Production",
                palette="Paired", ax=ax2)
    sns.stripplot(data=df_region, x="Region", y="Production",
                  color=".3", size=1.5, jitter=True, ax=ax2)
    ax2.set_xlabel("", fontsize=6)
    ax2.set_ylabel("Production", fontsize=6)
    ax2.tick_params(axis='both', labelsize=6)
    st.pyplot(fig2)

with row1[2]:
    st.markdown("##### 3) 시장 동향 반영: 가격 변동과 운송량 상관관계 분석")
    fig3, ax3 = plt.subplots(figsize=(4, 2.5))
    sns.heatmap(df_heat, annot=True, fmt=".1f", cmap="coolwarm",
                cbar=False, annot_kws={"size": 4}, ax=ax3)
    ax3.tick_params(axis='both', labelsize=6)
    st.pyplot(fig3)

# ───────────── 두 번째 줄 ─────────────
row2 = st.columns(3, gap="large")

with row2[0]:
    st.markdown("##### 4) 계절성 분석: 월별, 분기별 운송 패턴 분석")
    fig4, ax4 = plt.subplots(figsize=(4, 2.5))
    sns.lineplot(data=df_season, x="Month", y="Shipment", ci="sd", marker='o',
                 linewidth=0.8, markersize=2, ax=ax4,
                 palette=sns.color_palette("Paired"))
    ax4.set_xlabel("Month", fontsize=6)
    ax4.set_ylabel("Shipment", fontsize=6)
    ax4.tick_params(axis='both', labelsize=6)
    st.pyplot(fig4)

with row2[1]:
    st.markdown("##### 5) 농촌 상생: 농가 소득증대 및 지역경제 활성화")
    fig5, ax5 = plt.subplots(figsize=(4, 2.5))
    sns.scatterplot(data=df_market, x="Price", y="Volume",
                    s=8, color=sns.color_palette("Paired")[0], ax=ax5)
    sns.regplot(data=df_market, x="Price", y="Volume",
                scatter=False, color=sns.color_palette("Paired")[1], ax=ax5)
    ax5.set_xlabel("Price ($)", fontsize=6)
    ax5.set_ylabel("Volume", fontsize=6)
    ax5.tick_params(axis='both', labelsize=6)
    st.pyplot(fig5)

with row2[2]:
    st.markdown("##### 6) 탄소배출 계산: 정부 탄소중립 정책 기여도 측정")
    fig6, ax6 = plt.subplots(figsize=(1.0, 1.0), dpi=500)  # 극소형 + 선명
    colors = sns.color_palette("Paired")
    wedges, texts, autotexts = ax6.pie(
        df_carbon["Ratio"],
        labels=df_carbon["Category"],
        colors=colors[:5],
        autopct='%1.1f%%',
        textprops={'fontsize': 3, 'color': 'black'},
        wedgeprops=dict(width=0.35)
    )
    for text in texts:
        text.set_fontsize(3)
        text.set_color('black')
    ax6.set_title("")
    st.pyplot(fig6)

