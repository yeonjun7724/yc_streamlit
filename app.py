# app.py
import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import pydeck as pdk

# ✅ Mapbox 토큰 — 전역 설정으로 관리
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
pdk.settings.mapbox_api_key = MAPBOX_TOKEN

ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

# --------- 📌 Mapbox Directions API (C → D) ---------
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

# --------- 📌 Mapbox Optimization API (C → C → ... → D) ---------
def get_optimized_route(waypoints):
    coords = ";".join([f"{lon},{lat}" for lat, lon in waypoints])
    url = f"https://api.mapbox.com/optimized-trips/v1/mapbox/driving/{coords}"
    params = {
        "geometries": "geojson",
        "overview": "full",
        "source": "first",
        "destination": "last",
        "roundtrip": "false",
        "access_token": MAPBOX_TOKEN
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    coords = res.json()["trips"][0]["geometry"]["coordinates"]
    return LineString(coords)

# --------- 📌 데이터 불러오기 ---------
@st.cache_data
def load_data():
    gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
    gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)
    return gdf_asis, gdf_tobe

gdf_asis, gdf_tobe = load_data()
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# --------- 📌 pydeck Layer 생성 ---------
def create_pydeck_layers(points, line, label=""):
    scatter_data = []
    for p in points:
        scatter_data.append({"lat": p[0], "lon": p[1], "label": label})

    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=scatter_data,
        get_position='[lon, lat]',
        get_fill_color='[0, 200, 0]' if label == "C" else '[200, 0, 0]',
        get_radius=100
    )

    line_layer = pdk.Layer(
        "LineLayer",
        data=[{"path": [[coord[0], coord[1]] for coord in line.coords]}],
        get_path="path",
        get_width=5,
        get_color=[0, 0, 255]
    )

    return [scatter_layer, line_layer]

# --------- 📌 AS-IS pydeck ---------
def make_asis_pydeck(sorting_id):
    group = gdf_asis[gdf_asis["sorting_id"] == sorting_id]
    c_points = group[group["location_t"] == "C"]
    d_points = group[group["location_t"] == "D"]

    layers = []
    for _, c_row in c_points.iterrows():
        c_pt = c_row.geometry
        d_nearest = d_points.distance(c_pt).idxmin()
        d_pt = d_points.loc[d_nearest].geometry

        c_latlon = (c_pt.y, c_pt.x)
        d_latlon = (d_pt.y, d_pt.x)
        route_line = get_route(c_latlon, d_latlon)
        layers += create_pydeck_layers([c_latlon, d_latlon], route_line, label="C")

    view_state = pdk.ViewState(
        latitude=group.geometry.y.mean(),
        longitude=group.geometry.x.mean(),
        zoom=12
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v10"
    )

    return deck

# --------- 📌 TO-BE pydeck ---------
def make_tobe_pydeck(sorting_id):
    group = gdf_tobe[gdf_tobe["sorting_id"] == sorting_id]
    c_points = group[group["location_t"] == "C"].sort_values("stop_seq", ascending=False)
    d_points = group[group["location_t"] == "D"]

    c_coords = [(row.geometry.y, row.geometry.x) for _, row in c_points.iterrows()]
    d_geom = d_points.iloc[0].geometry
    d_latlon = (d_geom.y, d_geom.x)

    waypoints = c_coords + [d_latlon]
    route_line = get_optimized_route(waypoints)

    layers = create_pydeck_layers(waypoints, route_line, label="C")

    view_state = pdk.ViewState(
        latitude=group.geometry.y.mean(),
        longitude=group.geometry.x.mean(),
        zoom=12
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v10"
    )

    return deck

# --------- 📌 Streamlit Layout ---------
col1, col2 = st.columns(2)

with col1:
    st.markdown("### ⬅ AS-IS")
    try:
        deck1 = make_asis_pydeck(selected_id)
        st.pydeck_chart(deck1)
    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

with col2:
    st.markdown("### TO-BE ➡")
    try:
        deck2 = make_tobe_pydeck(selected_id)
        st.pydeck_chart(deck2)
    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
