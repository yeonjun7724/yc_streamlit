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

MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH    = "cb_asis_sample.shp"
TOBE_PATH    = "cb_tobe_sample.shp"
COMMON_TILE  = "CartoDB positron"

# 컬러 팔레트
palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]

# 데이터 로드
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 경로 선택
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# KPI 영역: ASIS 첫줄, TOBE 둘째줄
asis_cols = st.columns(4)
asis_cols[0].metric("ASIS 소요시간",    "--", help="기존 경로의 예상 소요시간")
asis_cols[1].metric("ASIS 최단거리",    "--", help="기존 경로의 실제 최단거리 합계")
asis_cols[2].metric("ASIS 물류비",      "--", help="기존 경로의 예상 물류비용")
asis_cols[3].metric("ASIS 탄소배출량",  "--", help="기존 경로의 예상 CO₂ 배출량")

tobe_cols = st.columns(4)
tobe_cols[0].metric("TOBE 소요시간",    "--", help="개선 경로의 예상 소요시간")

# TOBE 최단거리 계산
tobe_group = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]
tobe_dist = round(tobe_group["drive_dist"].sum(), 2)
tobe_cols[1].metric("TOBE 최단거리", f"{tobe_dist} km", help="개선 경로의 실제 최단거리 합계")

tobe_cols[2].metric("TOBE 물류비",      "--", help="개선 경로의 예상 물류비용")
tobe_cols[3].metric("TOBE 탄소배출량",  "--", help="개선 경로의 예상 CO₂ 배출량")

st.markdown("---")

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

col1, col2 = st.columns(2, gap="large")

# AS-IS
with col1:
    st.markdown("#### ⬅ AS-IS 경로")
    try:
        grp   = gdf_asis[gdf_asis["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"].reset_index()
        d_pts = grp[grp["location_t"] == "D"].reset_index()

        m  = Map(
            location=[grp.geometry.y.mean(), grp.geometry.x.mean()],
            zoom_start=12,
            tiles=COMMON_TILE
        )
        fg = FeatureGroup(name="ASIS")

        for idx, crow in c_pts.iterrows():
            color = palette[idx % len(palette)]
            c = crow.geometry
            d = d_pts.loc[d_pts.geometry.distance(c).idxmin()].geometry

            c_icon = BeautifyIcon(
                icon="map-pin", icon_shape="marker",
                background_color=color, border_color="#fff",
                text_color="#fff", number=idx+1
            )
            d_icon = BeautifyIcon(
                icon="flag-checkered", icon_shape="marker",
                background_color=color, border_color="#fff",
                text_color="#fff"
            )

            folium.Marker((c.y, c.x), icon=c_icon).add_to(fg)
            folium.Marker((d.y, d.x), icon=d_icon).add_to(fg)

            res = requests.get(
                f"https://api.mapbox.com/directions/v5/mapbox/driving/{c.x},{c.y};{d.x},{d.y}",
                params={"geometries":"geojson","overview":"simplified","access_token":MAPBOX_TOKEN}
            )
            res.raise_for_status()
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

# TO-BE
with col2:
    st.markdown("#### TOBE ➡ 개선 경로")
    try:
        grp   = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
        d     = grp[grp["location_t"] == "D"].iloc[0].geometry

        m  = Map(
            location=[grp.geometry.y.mean(), grp.geometry.x.mean()],
            zoom_start=12,
            tiles=COMMON_TILE
        )
        fg = FeatureGroup(name="TOBE")

        coords = []
        for idx, row in c_pts.iterrows():
            color = palette[idx % len(palette)]
            pt = row.geometry
            coords.append((pt.y, pt.x))

            c_icon = BeautifyIcon(
                icon="map-pin", icon_shape="marker",
                background_color=color, border_color="#fff",
                text_color="#fff", number=row["stop_seq"]
            )
            folium.Marker((pt.y, pt.x), icon=c_icon).add_to(fg)

        d_icon = BeautifyIcon(
            icon="flag-checkered", icon_shape="marker",
            background_color="#000", border_color="#fff",
            text_color="#fff"
        )
        folium.Marker((d.y, d.x), icon=d_icon).add_to(fg)

        for i in range(len(coords)):
            start = coords[i]
            end   = coords[i+1] if i < len(coords)-1 else (d.y, d.x)
            color = palette[i % len(palette)]
            tooltip = (
                f"C{c_pts.loc[i,'stop_seq']} → "
                + (f"C{c_pts.loc[i+1,'stop_seq']}" if i < len(coords)-1 else "D")
            )

            res = requests.get(
                f"https://api.mapbox.com/directions/v5/mapbox/driving/{start[1]},{start[0]};{end[1]},{end[0]}",
                params={"geometries":"geojson","overview":"simplified","access_token":MAPBOX_TOKEN}
            )
            res.raise_for_status()
            seg = res.json()["routes"][0]["geometry"]["coordinates"]

            GeoJson(
                LineString(seg),
                style_function=lambda feat, col=color: {"color": col, "weight": 5},
                tooltip=tooltip
            ).add_to(fg)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
