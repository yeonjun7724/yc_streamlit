import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, CircleMarker, GeoJson
from streamlit.components.v1 import html

# --- 설정 ---
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_asis_sample.shp"

# --- 데이터 로드 ---
@st.cache_data
def load_data():
    gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
    return gdf_asis

gdf_asis = load_data()
common_ids = sorted(set(gdf_asis["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# --- AS-IS 그룹 ---
group_asis = gdf_asis[gdf_asis["sorting_id"] == selected_id].dropna(subset=["geometry"])
c_points = group_asis[group_asis["location_t"] == "C"]
d_points = group_asis[group_asis["location_t"] == "D"]

# --- 중심점 계산 ---
lat_center = group_asis.geometry.y.mean()
lon_center = group_asis.geometry.x.mean()

if lat_center != lat_center or lon_center != lon_center:
    # NaN이면 fallback
    lat_center, lon_center = 0.0, 0.0

lat_center = float(lat_center)
lon_center = float(lon_center)

st.write("중심점 확인:", lat_center, lon_center, type(lat_center), type(lon_center))

m1 = Map(
    location=[lat_center, lon_center],
    zoom_start=12,
    width="100%",
    height="100%"
)
fg1 = FeatureGroup(name=f"ASIS {selected_id}")

for _, row in c_points.iterrows():
    c_pt = row.geometry
    d_idx = d_points.distance(c_pt).idxmin()
    d_pt = d_points.loc[d_idx].geometry

    c_latlon = (float(c_pt.y), float(c_pt.x))
    d_latlon = (float(d_pt.y), float(d_pt.x))

    st.write("C 좌표:", c_latlon, type(c_latlon[0]), type(c_latlon[1]))
    st.write("D 좌표:", d_latlon, type(d_latlon[0]), type(d_latlon[1]))

    CircleMarker(location=c_latlon, radius=4, color="green", fill=True).add_to(fg1)
    CircleMarker(location=d_latlon, radius=4, color="red", fill=True).add_to(fg1)

    # Mapbox Directions
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
    GeoJson(line).add_to(fg1)

fg1.add_to(m1)
folium.LayerControl(collapsed=False).add_to(m1)

st.markdown("### ⬅ AS-IS")
html(m1.get_root().render(), width="100%", height=800, scrolling=True)
