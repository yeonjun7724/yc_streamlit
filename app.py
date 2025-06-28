import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, CircleMarker, GeoJson
from streamlit.components.v1 import html

# 와이드 레이아웃
st.set_page_config(layout="wide")

MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

# 컬러 팔레트 (8가지)
palette = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
    "#ff7f00", "#ffff33", "#a65628", "#f781bf"
]

# 데이터 로드
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 선택박스
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# 맵 렌더 함수 (width 자동)
def render_map(m, height=600):
    html(m.get_root().render(), height=height)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### ⬅ AS-IS")
    try:
        grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"]
        d_pts = grp[grp["location_t"] == "D"]
        m = Map(location=[grp.geometry.y.mean(), grp.geometry.x.mean()], zoom_start=12)
        fg = FeatureGroup(name=f"ASIS {selected_id}")

        for idx, (_, crow) in enumerate(c_pts.iterrows()):
            color = palette[idx % len(palette)]
            c = crow.geometry
            # 가장 가까운 D 찾기
            d_idx = d_pts.geometry.distance(c).idxmin()
            d = d_pts.loc[d_idx].geometry

            c_ll = (c.y, c.x)
            d_ll = (d.y, d.x)

            # 세련된 원형 마커 (테두리 흰색, 내부 컬러)
            CircleMarker(
                location=c_ll, radius=8,
                color="white", weight=2,
                fill=True, fill_color=color, fill_opacity=0.9,
                tooltip=f"C ({idx+1})"
            ).add_to(fg)
            CircleMarker(
                location=d_ll, radius=8,
                color="white", weight=2,
                fill=True, fill_color=color, fill_opacity=0.9,
                tooltip="D"
            ).add_to(fg)

            # Mapbox 라우팅
            url = (
                f"https://api.mapbox.com/directions/v5/mapbox/driving/"
                f"{c.x},{c.y};{d.x},{d.y}"
            )
            res = requests.get(url, params={
                "geometries": "geojson",
                "overview": "simplified",
                "access_token": MAPBOX_TOKEN
            })
            res.raise_for_status()
            coords = res.json()["routes"][0]["geometry"]["coordinates"]
            line = LineString(coords)

            # 컬러 라인
            GeoJson(
                line,
                tooltip="C → D",
                style_function=lambda feat, col=color: {
                    "color": col, "weight": 4
                }
            ).add_to(fg)

        fg.add_to(m)
        render_map(m)
    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

with col2:
    st.markdown("### TO-BE ➡")
    try:
        grp = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"].sort_values("stop_seq", ascending=False)
        d_pt = grp[grp["location_t"] == "D"].iloc[0].geometry

        m = Map(location=[grp.geometry.y.mean(), grp.geometry.x.mean()], zoom_start=12)
        fg = FeatureGroup(name=f"TOBE {selected_id}")

        coords = []
        for idx, (_, row) in enumerate(c_pts.iterrows()):
            color = palette[idx % len(palette)]
            pt = row.geometry
            ll = (pt.y, pt.x)
            coords.append(ll)

            CircleMarker(
                location=ll, radius=8,
                color="white", weight=2,
                fill=True, fill_color=color, fill_opacity=0.9,
                tooltip=f"C{row['stop_seq']}"
            ).add_to(fg)

        # D 마커
        d_ll = (d_pt.y, d_pt.x)
        CircleMarker(
            location=d_ll, radius=8,
            color="white", weight=2,
            fill=True, fill_color="#000000", fill_opacity=0.9,
            tooltip="D"
        ).add_to(fg)

        # C→C 구간
        for i in range(len(coords) - 1):
            color = palette[i % len(palette)]
            lon1, lat1 = coords[i][1], coords[i][0]
            lon2, lat2 = coords[i+1][1], coords[i+1][0]
            url = (
                f"https://api.mapbox.com/directions/v5/mapbox/driving/"
                f"{lon1},{lat1};{lon2},{lat2}"
            )
            res = requests.get(url, params={
                "geometries": "geojson",
                "overview": "simplified",
                "access_token": MAPBOX_TOKEN
            })
            res.raise_for_status()
            seg = LineString(res.json()["routes"][0]["geometry"]["coordinates"])

            GeoJson(
                seg,
                tooltip=f"C{i+1} → C{i}",
                style_function=lambda feat, col=color: {
                    "color": col, "weight": 4
                }
            ).add_to(fg)

        # 마지막 C→D
        lon1, lat1 = coords[-1][1], coords[-1][0]
        lon2, lat2 = d_pt.x, d_pt.y
        url = (
            f"https://api.mapbox.com/directions/v5/mapbox/driving/"
            f"{lon1},{lat1};{lon2},{lat2}"
        )
        res = requests.get(url, params={
            "geometries": "geojson",
            "overview": "simplified",
            "access_token": MAPBOX_TOKEN
        })
        res.raise_for_status()
        seg = LineString(res.json()["routes"][0]["geometry"]["coordinates"])

        GeoJson(
            seg,
            tooltip="C → D",
            style_function=lambda feat, col=palette[(len(coords)-1) % len(palette)]: {
                "color": col, "weight": 4
            }
        ).add_to(fg)

        fg.add_to(m)
        render_map(m)
    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
