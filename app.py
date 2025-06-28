import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, GeoJson
from folium.plugins import BeautifyIcon
from streamlit.components.v1 import html

# 와이드 레이아웃
st.set_page_config(layout="wide")

# 상수
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1ZiIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH    = "cb_asis_sample.shp"
TOBE_PATH    = "cb_tobe_sample.shp"
COMMON_TILE  = "CartoDB positron"

# 컬러 팔레트
palette = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"
]

# 데이터 로드
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 경로 선택
common_ids  = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# 그룹별 데이터
asis_grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
tobe_grp = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]

# TOBE KPI 계산
# 1) TOBE 소요시간: 마지막 C 지점의 elapsed_mi
c_grp     = tobe_grp[tobe_grp["location_t"] == "C"].sort_values("stop_seq")
tobe_time = f"{c_grp['elapsed_mi'].iloc[-1]} 분" if not c_grp.empty and "elapsed_mi" in c_grp.columns else "--"
# 2) TOBE 최단거리: drive_dist 합계
tobe_dist = round(tobe_grp["drive_dist"].sum(), 2) if "drive_dist" in tobe_grp.columns else 0
# 3) TOBE 물류비: 최단거리 * 5000
tobe_cost = int(tobe_dist * 5000)

# KPI 표시
asis_cols = st.columns(4)
asis_cols[0].metric("ASIS 소요시간",   "--",                help="기존 경로의 예상 소요시간")
asis_cols[1].metric("ASIS 물류비",     "--",                help="기존 경로의 예상 물류비용")
asis_cols[2].metric("ASIS 탄소배출량", "--",                help="기존 경로의 예상 CO₂ 배출량")
asis_cols[3].metric("ASIS 최단거리",   "--",                help="기존 경로의 실제 최단거리 합계")

tobe_cols = st.columns(4)
tobe_cols[0].metric("TOBE 소요시간",   tobe_time,           help="개선 경로의 실제 소요시간 (마지막 C의 elapsed_mi)")
tobe_cols[1].metric("TOBE 최단거리",   f"{tobe_dist} km",   help="개선 경로의 실제 최단거리 합계")
tobe_cols[2].metric("TOBE 물류비",     f"{tobe_cost:,} 원", help="개선 경로의 예상 물류비용 (최단거리×5,000원)")
tobe_cols[3].metric("TOBE 탄소배출량", "--",                help="개선 경로의 예상 CO₂ 배출량")

st.markdown("---")

# 지도 렌더링 함수
def render_map(m, height=600):
    html(m.get_root().render(), height=height)

col1, col2 = st.columns(2, gap="large")

# AS-IS 맵
with col1:
    st.markdown("#### ⬅ AS-IS 경로")
    try:
        c_pts = asis_grp[asis_grp["location_t"] == "C"].reset_index()
        d_pts = asis_grp[asis_grp["location_t"] == "D"].reset_index()

        m  = Map(
            location=[asis_grp.geometry.y.mean(), asis_grp.geometry.x.mean()],
            zoom_start=12,
            tiles=COMMON_TILE
        )
        fg = FeatureGroup(name="ASIS")

        for idx, crow in c_pts.iterrows():
            color = palette[idx % len(palette)]
            c = crow.geometry
            d = d_pts.loc[d_pts.geometry.distance(c).idxmin()].geometry

            folium.Marker(
                (c.y, c.x),
                icon=BeautifyIcon(icon="map-pin",
                                  background_color=color,
                                  text_color="#fff",
                                  number=idx+1)
            ).add_to(fg)
            folium.Marker(
                (d.y, d.x),
                icon=BeautifyIcon(icon="flag-checkered",
                                  background_color=color,
                                  text_color="#fff")
            ).add_to(fg)

            res = requests.get(
                f"https://api.mapbox.com/directions/v5/mapbox/driving/{c.x},{c.y};{d.x},{d.y}",
                params={"geometries":"geojson","overview":"simplified","access_token":MAPBOX_TOKEN}
            )
            coords = res.json()["routes"][0]["geometry"]["coordinates"]

            GeoJson(
                LineString(coords),
                style_function=lambda feat, col=color: {"color": col, "weight": 5},
                tooltip=f"C{idx+1} → D"
            ).add_to(fg)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

# TO-BE 맵
with col2:
    st.markdown("#### TO-BE ➡ 개선 경로")
    try:
        c_pts = tobe_grp[tobe_grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
        d     = tobe_grp[tobe_grp["location_t"] == "D"].geometry.iloc[0]

        m  = Map(
            location=[tobe_grp.geometry.y.mean(), tobe_grp.geometry.x.mean()],
            zoom_start=12,
            tiles=COMMON_TILE
        )
        fg = FeatureGroup(name="TOBE")

        for idx, row in c_pts.iterrows():
            color = palette[idx % len(palette)]
            pt = row.geometry
            folium.Marker(
                (pt.y, pt.x),
                icon=BeautifyIcon(icon="map-pin",
                                  background_color=color,
                                  text_color="#fff",
                                  number=row["stop_seq"])
            ).add_to(fg)

        folium.Marker(
            (d.y, d.x),
            icon=BeautifyIcon(icon="flag-checkered",
                              background_color="#000",
                              text_color="#fff")
        ).add_to(fg)

        for i in range(len(c_pts)):
            start = (c_pts.geometry.y.iloc[i], c_pts.geometry.x.iloc[i])
            end   = (c_pts.geometry.y.iloc[i+1], c_pts.geometry.x.iloc[i+1]) if i < len(c_pts)-1 else (d.y, d.x)
            color = palette[i % len(palette)]

            res = requests.get(
                f"https://api.mapbox.com/directions/v5/mapbox/driving/{start[1]},{start[0]};{end[1]},{end[0]}",
                params={"geometries":"geojson","overview":"simplified","access_token":MAPBOX_TOKEN}
            )
            coords = res.json()["routes"][0]["geometry"]["coordinates"]

            GeoJson(
                LineString(coords),
                style_function=lambda feat, col=color: {"color": col, "weight": 5},
                tooltip=(
                    f"C{c_pts.stop_seq.iloc[i]} → "
                    + (f"C{c_pts.stop_seq.iloc[i+1]}" if i < len(c_pts)-1 else "D")
                )
            ).add_to(fg)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
