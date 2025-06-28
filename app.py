import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
from folium import Map, FeatureGroup, CircleMarker, GeoJson
from streamlit.components.v1 import html

# 스트림릿을 와이드 모드로 설정
st.set_page_config(layout="wide")

MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

# 데이터 로드
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 공통 sorting_id 목록
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

# 두 개의 컬럼 생성
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### ⬅ AS-IS")
    try:
        grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"]
        d_pts = grp[grp["location_t"] == "D"]
        m = Map(location=[grp.geometry.y.mean(), grp.geometry.x.mean()], zoom_start=12)
        fg = FeatureGroup(name=f"ASIS {selected_id}")
        for _, crow in c_pts.iterrows():
            c = crow.geometry
            # D 지점 중 가장 가까운 포인트 찾기
            d_idx = d_pts.geometry.distance(c).idxmin()
            d = d_pts.loc[d_idx].geometry
            c_ll = (c.y, c.x)
            d_ll = (d.y, d.x)
            # 마커 추가
            CircleMarker(location=c_ll, radius=4, color="green", fill=True, tooltip="C").add_to(fg)
            CircleMarker(location=d_ll, radius=4, color="red", fill=True, tooltip="D").add_to(fg)
            # Mapbox 경로 요청 및 그리기
            lon1, lat1 = c.x, c.y
            lon2, lat2 = d.x, d.y
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
            GeoJson(line, tooltip="C → D").add_to(fg)
        fg.add_to(m)
        html(m.get_root().render(), height=600, width="100%")
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
        # C 포인트들에 마커 추가
        for _, row in c_pts.iterrows():
            pt = row.geometry
            ll = (pt.y, pt.x)
            coords.append(ll)
            CircleMarker(location=ll, radius=4, color="green", fill=True, tooltip=f"C{row['stop_seq']}").add_to(fg)
        # D 포인트 마커
        d_ll = (d_pt.y, d_pt.x)
        CircleMarker(location=d_ll, radius=4, color="red", fill=True, tooltip="D").add_to(fg)
        # C → C 경로
        for i in range(len(coords) - 1):
            (lat1, lon1), (lat2, lon2) = coords[i], coords[i+1]
            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{lon1},{lat1};{lon2},{lat2}"
            params = {
                "geometries": "geojson",
                "overview": "simplified",
                "access_token": MAPBOX_TOKEN
            }
            res = requests.get(url, params=params)
            res.raise_for_status()
            cts = res.json()["routes"][0]["geometry"]["coordinates"]
            GeoJson(LineString(cts), tooltip=f"C{i+1} → C{i}").add_to(fg)
        # 마지막 C → D 경로
        lon1, lat1 = coords[-1][1], coords[-1][0]
        lon2, lat2 = d_pt.x, d_pt.y
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{lon1},{lat1};{lon2},{lat2}"
        params = {
            "geometries": "geojson",
            "overview": "simplified",
            "access_token": MAPBOX_TOKEN
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        cts = res.json()["routes"][0]["geometry"]["coordinates"]
        GeoJson(LineString(cts), tooltip="C → D").add_to(fg)
        fg.add_to(m)
        html(m.get_root().render(), height=600, width="100%")
    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
