import streamlit as st
import geopandas as gpd
from shapely import wkt
from shapely.geometry import LineString
import requests
import folium
from folium import Map, FeatureGroup, CircleMarker, GeoJson
from streamlit.components.v1 import html

st.set_page_config(layout="wide")

# ✅ 당신의 MAPBOX 토큰으로 교체
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"

ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

# ──────────────
# 1) 데이터 로드
@st.cache_data
def load_data():
    asis = gpd.read_file(ASIS_PATH)
    tobe = gpd.read_file(TOBE_PATH)

    if isinstance(asis.geometry.iloc[0], str):
        asis["geometry"] = asis["geometry"].apply(wkt.loads)
    if isinstance(tobe.geometry.iloc[0], str):
        tobe["geometry"] = tobe["geometry"].apply(wkt.loads)

    asis = gpd.GeoDataFrame(asis, geometry="geometry", crs="EPSG:4326").to_crs(4326)
    tobe = gpd.GeoDataFrame(tobe, geometry="geometry", crs="EPSG:4326").to_crs(4326)

    return asis, tobe

asis_gdf, tobe_gdf = load_data()

# 컬럼 확인
st.write("✅ ASIS 컬럼:", asis_gdf.columns)
st.write("✅ TOBE 컬럼:", tobe_gdf.columns)

# ──────────────
# 2) 그룹 ID 설정
asis_group_col = "org_job_id"
tobe_group_col = "job_id"

common_ids = sorted(set(asis_gdf[asis_group_col]) & set(tobe_gdf[tobe_group_col]))
selected_id = st.selectbox("📌 경로 선택", common_ids)

# ──────────────
# 3) 그룹 필터링
asis_group = asis_gdf[asis_gdf[asis_group_col] == selected_id]
tobe_group = tobe_gdf[tobe_gdf[tobe_group_col] == selected_id]

asis_center = [asis_group.geometry.y.mean(), asis_group.geometry.x.mean()]
tobe_center = [tobe_group.geometry.y.mean(), tobe_group.geometry.x.mean()]

# ──────────────
# 4) AS-IS 지도
asis_map = Map(location=asis_center, zoom_start=12)
asis_fg = FeatureGroup(name=f"ASIS {selected_id}")

# ASIS는 각 포인트 표시 + 도착점은 가장 먼 포인트로 가정
asis_points = asis_group.copy()
asis_points["center_dist"] = asis_points.geometry.distance(asis_group.unary_union.centroid)
asis_points = asis_points.sort_values("center_dist", ascending=False)

for _, row in asis_points.iterrows():
    pt = row.geometry
    latlon = (pt.y, pt.x)
    CircleMarker(latlon, radius=4, color="green", fill=True, tooltip="ASIS Point").add_to(asis_fg)

# 중심점 ↔ 가장 먼 점 경로 예시 (단일 경로)
origin = [asis_group.unary_union.centroid.y, asis_group.unary_union.centroid.x]
dest = [asis_points.iloc[0].geometry.y, asis_points.iloc[0].geometry.x]

url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
res = requests.get(url, params={"geometries":"geojson","overview":"simplified","access_token":MAPBOX_TOKEN})
res.raise_for_status()
coords = res.json()["routes"][0]["geometry"]["coordinates"]
GeoJson(LineString(coords), tooltip="ASIS Route").add_to(asis_fg)

asis_fg.add_to(asis_map)
folium.LayerControl(collapsed=False).add_to(asis_map)

# ──────────────
# 5) TO-BE 지도
tobe_map = Map(location=tobe_center, zoom_start=12)
tobe_fg = FeatureGroup(name=f"TOBE {selected_id}")

# stop_seq 내림차순 정렬로 순서 설정
tobe_points = tobe_group.sort_values("stop_seq", ascending=False)

c_coords = []
for _, row in tobe_points.iterrows():
    pt = row.geometry
    latlon = (pt.y, pt.x)
    c_coords.append(latlon)
    CircleMarker(latlon, radius=4, color="green", fill=True, tooltip=f"stop_seq: {row['stop_seq']}").add_to(tobe_fg)

# 경유지 순서대로 연결
for i in range(len(c
