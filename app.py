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
import numpy as np

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

        for i, row in c_pts.iterrows():
            folium.Marker([row.geometry.y, row.geometry.x], icon=DivIcon(
                icon_size=(30,30), icon_anchor=(15,15),
                html=f'<div style="font-size:14px; color:#fff; background:{palette[i % len(palette)]}; border-radius:50%; width:30px; height:30px; text-align:center; line-height:30px;">{i+1}</div>'
            )).add_to(fg)

        folium.Marker([d_pt.y, d_pt.x], icon=folium.Icon(icon="flag-checkered", prefix="fa", color="red")).add_to(fg)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[다타소 에러] {e}")

# ───────────── 정책·활용방안 + 샘플 그래프 ─────────────
st.markdown("---")
st.markdown("#### 📌 정책·활용방안")
st.markdown("""
✅ 실시간 교통정보: 도로 상황 반영한 동적 경로 조정  
✅ 탄소배출 계산: 정부 탄소중립 정책 기여도 측정  
✅ 축산업 혁신: 스마트팜 정책과 연계한 디지털 전환  
✅ 농촌 상생: 농가 소득증대 및 지역경제 활성화  
✅ 계절성 분석: 월별, 분기별 운송 패턴 분석  
✅ 지역별 특성: 권역별 운송 수요 변동성 예측  
✅ 시장 동향 반영: 가격 변동과 운송량 상관관계 분석
""")

# ───────────── 샘플 그래프 영역 ─────────────
st.markdown("#### 📊 분석 샘플 그래프 (예시)")

# 1) 계절성 분석: 월별 운송량
months = np.arange(1, 13)
volumes = np.random.randint(50, 150, size=12)
fig1, ax1 = plt.subplots()
ax1.plot(months, volumes, marker='o', linestyle='-', color='#1f77b4')
ax1.set_title("월별 운송량 추이 (계절성 분석)")
ax1.set_xlabel("월")
ax1.set_ylabel("운송량 (톤)")
ax1.grid(True)

# 2) 가격 변동 vs 운송량
prices = np.random.uniform(1000, 5000, 30)
volumes = np.random.uniform(40, 160, 30)
fig2, ax2 = plt.subplots()
ax2.scatter(prices, volumes, color='#ff7f0e', alpha=0.7)
ax2.set_title("가격 변동 vs 운송량 (시장 동향)")
ax2.set_xlabel("가격 (원/kg)")
ax2.set_ylabel("운송량 (톤)")
ax2.grid(True)

# 3) 권역별 운송 수요 변동성
regions = ['권역 A', '권역 B', '권역 C']
data = [np.random.normal(100, 15, 50), np.random.normal(120, 20, 50), np.random.normal(90, 10, 50)]
fig3, ax3 = plt.subplots()
ax3.boxplot(data, labels=regions)
ax3.set_title("권역별 운송 수요 변동성 (지역별 특성)")
ax3.set_ylabel("운송량 (톤)")
ax3.grid(True)

# 4) 농촌 상생: 농가별 소득 증대
farmers = ['농가 A', '농가 B', '농가 C', '농가 D']
income = np.random.randint(5, 15, size=4)
fig4, ax4 = plt.subplots()
ax4.bar(farmers, income, color='#2ca02c')
ax4.set_title("농가별 예상 소득 증대 (농촌 상생)")
ax4.set_ylabel("소득 증대율 (%)")
ax4.grid(axis='y')

col_g1, col_g2 = st.columns(2)
with col_g1:
    st.pyplot(fig1)
    st.pyplot(fig3)
with col_g2:
    st.pyplot(fig2)
    st.pyplot(fig4)
