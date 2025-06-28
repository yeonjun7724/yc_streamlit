# app.py
import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
from shapely import wkt
import folium
from folium import Map, FeatureGroup, CircleMarker, GeoJson
from streamlit.components.v1 import html

# ────────────────────────────────
# 1) Streamlit 전체화면
st.set_page_config(layout="wide")

# ────────────────────────────────
# 2) 설정
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

# ────────────────────────────────
# 3) Shapefile 로드 + geometry 안전 검사
@st.cache_data
def load_data():
    asis = gpd.read_file(ASIS_PATH)
    tobe = gpd.read_file(TOBE_PATH)

    # geometry가 문자열이면 shapely로 변환
    if isinstance(asis.geometry.iloc[0], str):
        asis["geometry"] = asis["geometry"].apply(wkt.loads)
    if isinstance(tobe.geometry.iloc[0], str):
        tobe["geometry"] = tobe["geometry"].apply(wkt.loads)

    asis = asis.to_crs(4326)
    tobe = tobe.to_crs(4326)

    return asis, tobe

asis_gdf, tobe_gdf = load_data()

# ────────────────────────────────
# 4) 공통 sorting_id 선택
common_ids = sorted(set(asis_gdf["sorting_id"]) & set(tobe_gdf["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# ────────────────────────────────
# 5) 선택된 경로 필터링
asis_group = asis_gdf[asis_gdf["sorting_id"] == selected_id]
tobe_group = tobe_gdf[tobe_gdf["sorting_id"] == selected_id]

# ────────────────────────────────
# 6) 중심좌표
asis_center = [asis_group.geometry.y.mean(), asis_group.geometry.x.mean()]
tobe_center = [tobe_group.geometry.y.mean(), tobe_group.geometry.x.mean()]

# ────────────────────────────────
# 7) AS-IS 지도
asis_map = Map(location=asis_center, zoom_start=12)
asis_fg = FeatureGroup(name=f"ASIS {selected_id}")

asis_c = asis_group[asis_group["location_t"] == "C"]
asis_d = asis_group[asis_group["location_t"] == "D"]

for _, c_row in asis_c.iterrows():
    c_pt = c_row.geometry
    d_idx = asis_d.geometry.distance(c_pt).idxmin()
    d_pt = asis_d.loc[d_idx].geometry

    c_latlon = (c_pt.y, c_pt.x)
    d_latlon = (d_pt.y, d_pt.x)

    CircleMarker(c_latlon, radius=4, color="green", fill=True, tooltip="C").add_to(asis_fg)
    CircleMarker(d_latlon, radius=4, color="red", fill=True, tooltip="D").add_to(asis_fg)

    # Mapbox Directions API
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{c_latlon[1]},{c_latlon[0]};{d_latlon[1]},{d_latlon[0]}"
    params = {
        "geometries": "geojson",
        "overview": "simplified",
        "access_token": MAPBOX_TOKEN
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    coords = res.json()["routes"][0]["geometry"]["coordinates"]
    line = LineString(coords)

    GeoJson(line, tooltip="C → D").add_to(asis_fg)

asis_fg.add_to(asis_map)
folium.LayerControl(collapsed=False).add_to(asis_map)

# ────────────────────────────────
# 8) TO-BE 지도
tobe_map = Map(location=tobe_center, zoom_start=12)
tobe_fg = FeatureGroup(name=f"TOBE {selected_id}")

tobe_c = tobe_group[tobe_group["location_t"] == "C"].sort_values("stop_seq", ascending=False)
tobe_d = tobe_group[tobe_group["location_t"] == "D"]

c_coords = []
for _, row in tobe_c.iterrows():
    pt = row.geometry
    latlon = (pt.y, pt.x)
    c_coords.append(latlon)
    CircleMarker(latlon, radius=4, color="green", fill=True, tooltip=f"C{row['stop_seq']}").add_to(tobe_fg)

d_geom = tobe_d.iloc[0].geometry
d_latlon = (d_geom.y, d_geom.x)
CircleMarker(d_latlon, radius=4, color="red", fill=True, tooltip="D").add_to(tobe_fg)

# C → C → ... → D
for i in range(len(c_coords) - 1):
    origin, dest = c_coords[i], c_coords[i+1]
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
    res = requests.get(url, params={"geometries":"geojson", "overview":"simplified", "access_token":MAPBOX_TOKEN})
    res.raise_for_status()
    coords = res.json()["routes"][0]["geometry"]["coordinates"]
    GeoJson(LineString(coords), tooltip=f"C{i+1} → C{i}").add_to(tobe_fg)

# 마지막 C → D
origin, dest = c_coords[-1], d_latlon
url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
res = requests.get(url, params={"geometries":"geojson", "overview":"simplified", "access_token":MAPBOX_TOKEN})
res.raise_for_status()
coords = res.json()["routes"][0]["geometry"]["coordinates"]
GeoJson(LineString(coords), tooltip="C → D").add_to(tobe_fg)

tobe_fg.add_to(tobe_map)
folium.LayerControl(collapsed=False).add_to(tobe_map)

# ────────────────────────────────
# 9) Folium 렌더 함수
def render_folium_map(m, width="100%", height=800):
    html(m.get_root().render(), height=height, width=width)

# ────────────────────────────────
# 10) 두 지도를 가로로 출력
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("⬅ AS-IS")
    try:
        render_folium_map(asis_map)
    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

with col2:
    st.subheader("TO-BE ➡")
    try:
        render_folium_map(tobe_map)
    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
