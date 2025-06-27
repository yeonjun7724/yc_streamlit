# app.py
import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, CircleMarker, GeoJson
from streamlit.components.v1 import html

MAPBOX_TOKEN = "YOUR_MAPBOX_TOKEN"  # 꼭 본인 토큰으로 교체하세요
ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

def get_route(origin, destination):
    lon1, lat1 = origin[1], origin[0]
    lon2, lat2 = destination[1], destination[0]
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {
        "geometries": "geojson",
        "overview": "simplified",
        "access_token": MAPBOX_TOKEN
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    coords = res.json()["routes"][0]["geometry"]["coordinates"]
    return LineString(coords)

@st.cache_data
def load_data():
    gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
    gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)
    return gdf_asis, gdf_tobe

gdf_asis, gdf_tobe = load_data()
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

def make_asis_map(sorting_id):
    group = gdf_asis[gdf_asis["sorting_id"] == sorting_id]
    c_points = group[group["location_t"] == "C"]
    d_points = group[group["location_t"] == "D"]
    m = Map(location=[group.geometry.y.mean(), group.geometry.x.mean()], zoom_start=12)
    fg = FeatureGroup(name=f"ASIS {sorting_id}")
    for c_idx, c_row in c_points.iterrows():
        c_pt = c_row.geometry
        d_nearest = d_points.geometry.distance(c_pt).idxmin()
        d_pt = d_points.loc[d_nearest].geometry
        c_latlon = (c_pt.y, c_pt.x)
        d_latlon = (d_pt.y, d_pt.x)
        CircleMarker(location=c_latlon, radius=4, color="green", fill=True, tooltip=f"C").add_to(fg)
        CircleMarker(location=d_latlon, radius=4, color="red", fill=True, tooltip=f"D").add_to(fg)
        line = get_route(c_latlon, d_latlon)
        GeoJson(line, tooltip="C → D").add_to(fg)
    fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m

def make_tobe_map(sorting_id):
    group = gdf_tobe[gdf_tobe["sorting_id"] == sorting_id]
    c_points = group[group["location_t"] == "C"].sort_values("stop_seq", ascending=False)
    d_points = group[group["location_t"] == "D"]
    m = Map(location=[group.geometry.y.mean(), group.geometry.x.mean()], zoom_start=12)
    fg = FeatureGroup(name=f"TOBE {sorting_id}")
    c_coords = []
    for _, row in c_points.iterrows():
        pt = row.geometry
        latlon = (pt.y, pt.x)
        c_coords.append(latlon)
        CircleMarker(location=latlon, radius=4, color="green", fill=True, tooltip=f"C{row['stop_seq']}").add_to(fg)
    d_geom = d_points.iloc[0].geometry
    d_latlon = (d_geom.y, d_geom.x)
    CircleMarker(location=d_latlon, radius=4, color="red", fill=True, tooltip="D").add_to(fg)
    for i in range(len(c_coords) - 1):
        line = get_route(c_coords[i], c_coords[i+1])
        GeoJson(line, tooltip=f"C{i+1} → C{i}").add_to(fg)
    line = get_route(c_coords[-1], d_latlon)
    GeoJson(line, tooltip="C → D").add_to(fg)
    fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m

def render_folium_map(m, width=500, height=500):
    html(m.get_root().render(), height=height, width=width)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ⬅ AS-IS")
    try:
        m1 = make_asis_map(selected_id)
        render_folium_map(m1)
    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

with col2:
    st.markdown("### TO-BE ➡")
    try:
        m2 = make_tobe_map(selected_id)
        render_folium_map(m2)
    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
