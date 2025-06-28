import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, GeoJson, Icon
from streamlit.components.v1 import html

# 와이드 레이아웃
st.set_page_config(layout="wide")

# 상수
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH    = "cb_asis_sample.shp"
TOBE_PATH    = "cb_tobe_sample.shp"
COMMON_TILE  = "CartoDB positron"

# 컬러 팔레트
palette = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"
]

# 데이터 로드 (WGS84)
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 경로 선택
common_ids  = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("경로 선택 (sorting_id)", common_ids)

# 그룹별 데이터
asis_grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
tobe_grp = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]

# KPI 계산 (TOBE만 로직)
c_grp         = tobe_grp[tobe_grp["location_t"] == "C"].sort_values("stop_seq")
tobe_time     = f"{c_grp['elapsed_mi'].iloc[-1]} 분" if not c_grp.empty and "elapsed_mi" in c_grp.columns else "--"
tobe_dist     = round(tobe_grp["drive_dist"].sum(), 2) if "drive_dist" in tobe_grp.columns else 0
tobe_cost     = int(tobe_dist * 5000)
tobe_emission = round(tobe_dist * 0.65, 2)

# KPI 표시
asis_cols = st.columns(4)
asis_cols[0].metric("ASIS 소요시간",   "--")
asis_cols[1].metric("ASIS 최단거리",   "--")
asis_cols[2].metric("ASIS 물류비",     "--")
asis_cols[3].metric("ASIS 탄소배출량", "--")

tobe_cols = st.columns(4)
tobe_cols[0].metric("TOBE 소요시간",   tobe_time)
tobe_cols[1].metric("TOBE 최단거리",   f"{tobe_dist} km")
tobe_cols[2].metric("TOBE 물류비",     f"{tobe_cost:,} 원")
tobe_cols[3].metric("TOBE 탄소배출량", f"{tobe_emission} kg CO2")

st.markdown("---")

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

col1, col2 = st.columns(2, gap="large")

# ── AS-IS 경로
with col1:
    st.markdown("#### ⬅ AS-IS 경로")
    m = Map(
        location=[asis_grp.geometry.y.mean(), asis_grp.geometry.x.mean()],
        zoom_start=12, tiles=COMMON_TILE
    )
    fg = FeatureGroup(name="ASIS")

    c_pts = asis_grp[asis_grp["location_t"] == "C"].reset_index()
    d_pts = asis_grp[asis_grp["location_t"] == "D"].reset_index()

    for idx, crow in c_pts.iterrows():
        color = palette[idx % len(palette)]
        c = crow.geometry
        d = d_pts.loc[d_pts.geometry.distance(c).idxmin()].geometry

        # C 마커: 트럭 아이콘
        folium.Marker(
            (c.y, c.x),
            icon=Icon(icon="truck", prefix="fa", color=color)
        ).add_to(fg)

        # D 마커: 깃발 아이콘
        folium.Marker(
            (d.y, d.x),
            icon=Icon(icon="flag-checkered", prefix="fa", color=color)
        ).add_to(fg)

        # 경로 선: Mapbox → fallback 직선
        res = requests.get(
            f"https://api.mapbox.com/directions/v5/mapbox/driving/{c.x},{c.y};{d.x},{d.y}",
            params={"geometries":"geojson","overview":"simplified","access_token":MAPBOX_TOKEN}
        )
        data = res.json()
        routes = data.get("routes") or []
        if routes:
            coords = routes[0]["geometry"]["coordinates"]
            line = LineString(coords)
            style = {"color": color, "weight": 5}
        else:
            # 경로 없을 때는 직선, 점선으로 표시
            line = LineString([(c.x, c.y), (d.x, d.y)])
            style = {"color": color, "weight": 3, "dashArray": "5,5"}

        GeoJson(
            line,
            style_function=lambda feat, style=style: style,
            tooltip=f"C{idx+1} → D"
        ).add_to(fg)

    fg.add_to(m)
    render_map(m)

# ── TO-BE 경로
with col2:
    st.markdown("#### TO-BE ➡ 개선 경로")
    m = Map(
        location=[tobe_grp.geometry.y.mean(), tobe_grp.geometry.x.mean()],
        zoom_start=12, tiles=COMMON_TILE
    )
    fg = FeatureGroup(name="TOBE")

    c_pts = tobe_grp[tobe_grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
    d     = tobe_grp[tobe_grp["location_t"] == "D"].geometry.iloc[0]

    # C 지점 마커(트럭)
    for _, row in c_pts.iterrows():
        color = palette[row.name % len(palette)]
        folium.Marker(
            (row.geometry.y, row.geometry.x),
            icon=Icon(icon="truck", prefix="fa", color=color)
        ).add_to(fg)

    # D 지점 마커(깃발)
    folium.Marker(
        (d.y, d.x),
        icon=Icon(icon="flag-checkered", prefix="fa", color="#000")
    ).add_to(fg)

    # 구간별 라인 연결
    for i in range(len(c_pts)):
        start = (c_pts.geometry.y.iloc[i], c_pts.geometry.x.iloc[i])
        end   = (
            (c_pts.geometry.y.iloc[i+1], c_pts.geometry.x.iloc[i+1])
            if i < len(c_pts)-1 else (d.y, d.x)
        )
        color = palette[i % len(palette)]

        res = requests.get(
            f"https://api.mapbox.com/directions/v5/mapbox/driving/{start[1]},{start[0]};{end[1]},{end[0]}",
            params={"geometries":"geojson","overview":"simplified","access_token":MAPBOX_TOKEN}
        )
        data = res.json()
        routes = data.get("routes") or []
        if routes:
            coords = routes[0]["geometry"]["coordinates"]
            line = LineString(coords)
            style = {"color": color, "weight": 5}
        else:
            line = LineString([(start[1], start[0]), (end[1], end[0])])
