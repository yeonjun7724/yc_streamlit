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

# 공통 배경지도
COMMON_TILE = "CartoDB positron"

# 컬러 팔레트
palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]

# KPI 영역
k1, k2, k3, k4 = st.columns(4)
k1.metric("ASIS 소요시간", "--")
k2.metric("TOBE 소요시간", "--")
k3.metric("물류비", "--")
k4.metric("탄소배출량", "--")

st.markdown("---")

# 데이터 로드
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 경로 선택
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

col1, col2 = st.columns(2, gap="large")

# AS-IS
with col1:
    st.markdown("#### ⬅ AS-IS 경로")
    try:
        grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"].reset_index()
        d_pts = grp[grp["location_t"] == "D"].reset_index()

        m = Map(
            location=[grp.geometry.y.mean(), grp.geometry.x.mean()],
            zoom_start=12,
            tiles=COMMON_TILE
        )
        fg = FeatureGroup(name="ASIS")

        for idx, crow in c_pts.iterrows():
            color = palette[idx % len(palette)]
            c = crow.geometry
            # 가장 가까운 D
            d_idx = d_pts.geometry.distance(c).idxmin()
            d = d_pts.loc[d_idx].geometry

            # 아이콘
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

            # 경로 그리기
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
    st.markdown("#### TO-BE ➡ 개선 경로")
    try:
        grp = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
        d = grp[grp["location_t"] == "D"].iloc[0].geometry

        m = Map(
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

        # D 아이콘
        d_icon = BeautifyIcon(
            icon="flag-checkered", icon_shape="marker",
            background_color="#000", border_color="#fff",
            text_color="#fff"
        )
        folium.Marker((d.y, d.x), icon=d_icon).add_to(fg)

        # C→C and C→D
        for i in range(len(coords)):
            start = coords[i]
            end = coords[i+1] if i < len(coords)-1 else (d.y, d.x)
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
