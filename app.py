# app.py
import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, CircleMarker, GeoJson
from streamlit.components.v1 import html

# --------- 기본 설정 ---------
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

# --------- 데이터 로드 ---------
@st.cache_data
def load_data():
    gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
    gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)
    return gdf_asis, gdf_tobe

gdf_asis, gdf_tobe = load_data()
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# --------- 지도 준비: AS-IS ---------
group_asis = gdf_asis[gdf_asis["sorting_id"] == selected_id]
c_points_asis = group_asis[group_asis["location_t"] == "C"]
d_points_asis = group_asis[group_asis["location_t"] == "D"]

m1 = Map(
    location=[group_asis.geometry.y.mean(), group_asis.geometry.x.mean()],
    zoom_start=12,
    width="100%",
    height="100%"
)
fg1 = FeatureGroup(name=f"ASIS {selected_id}")

for idx, row in c_points_asis.iterrows():
    c_pt = row.geometry
    d_idx = d_points_asis.geometry.distance(c_pt).idxmin()
    d_pt = d_points_asis.loc[d_idx].geometry

    c_latlon = (c_pt.y, c_pt.x)
    d_latlon = (d_pt.y, d_pt.x)

    CircleMarker(location=c_latlon, radius=4, color="green", fill=True, tooltip="C").add_to(fg1)
    CircleMarker(location=d_latlon, radius=4, color="red", fill=True, tooltip="D").add_to(fg1)

    lon1, lat1 = c_latlon[1], c_latlon[0]
    lon2, lat2 = d_latlon[1], d_latlon[0]
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {
        "geometries": "geojson",
        "overview": "simplified",
        "access_token": MAPBOX_TOKEN
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    coords = res.json()["routes"][0]["geometry"]["coordinates"]
    line = LineString(coords)
    GeoJson(line, tooltip="C → D").add_to(fg1)

fg1.add_to(m1)
folium.LayerControl(collapsed=False).add_to(m1)

# --------- 지도 준비: TO-BE ---------
group_tobe = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]
c_points_tobe = group_tobe[group_tobe["location_t"] == "C"].sort_values("stop_seq", ascending=False)
d_points_tobe = group_tobe[group_tobe["location_t"] == "D"]

m2 = Map(
    location=[group_tobe.geometry.y.mean(), group_tobe.geometry.x.mean()],
    zoom_start=12,
    width="100%",
    height="100%"
)
fg2 = FeatureGroup(name=f"TOBE {selected_id}")

c_coords = []
for _, row in c_points_tobe.iterrows():
    pt = row.geometry
    latlon = (pt.y, pt.x)
    c_coords.append(latlon)
    CircleMarker(location=latlon, radius=4, color="green", fill=True, tooltip=f"C{row['stop_seq']}").add_to(fg2)

d_geom = d_points_tobe.iloc[0].geometry
d_latlon = (d_geom.y, d_geom.x)
CircleMarker(location=d_latlon, radius=4, color="red", fill=True, tooltip="D").add_to(fg2)

for i in range(len(c_coords) - 1):
    lon1, lat1 = c_coords[i][1], c_coords[i][0]
    lon2, lat2 = c_coords[i+1][1], c_coords[i+1][0]
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {
        "geometries": "geojson",
        "overview": "simplified",
        "access_token": MAPBOX_TOKEN
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    coords = res.json()["routes"][0]["geometry"]["coordinates"]
    line = LineString(coords)
    GeoJson(line, tooltip=f"C{i+1} → C{i}").add_to(fg2)

lon1, lat1 = c_coords[-1][1], c_coords[-1][0]
lon2, lat2 = d_latlon[1], d_latlon[0]
url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{lon1},{lat1};{lon2},{lat2}"
params = {
    "geometries": "geojson",
    "overview": "simplified",
    "access_token": MAPBOX_TOKEN
}
res = requests.get(url, params=params)
res.raise_for_status()
coords = res.json()["routes"][0]["geometry"]["coordinates"]
line = LineString(coords)
GeoJson(line, tooltip="C → D").add_to(fg2)

fg2.add_to(m2)
folium.LayerControl(collapsed=False).add_to(m2)

# --------- 화면 출력 ---------
col1, col2 = st.columns(2)

with col1:
    st.markdown("### ⬅ AS-IS")
    try:
        html(m1.get_root().render(), width="100%", height=800, scrolling=True)
    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

with col2:
    st.markdown("### TO-BE ➡")
    try:
        html(m2.get_root().render(), width="100%", height=800, scrolling=True)
    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
