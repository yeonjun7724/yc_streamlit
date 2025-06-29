import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, GeoJson
from folium.features import DivIcon
from streamlit.components.v1 import html

# 와이드 레이아웃
st.set_page_config(layout="wide")

# 상수
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_tobe_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"
COMMON_TILE = "CartoDB positron"

# 컬러 팔레트
palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]

# 데이터 로드 (WGS84)
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 경로 선택
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("경로 선택 (sorting_id)", common_ids)

# 그룹별 데이터
asis_grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
tobe_grp = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]

# KPI 표시
asis_cols = st.columns(4)
tobe_cols = st.columns(4)
st.markdown("---")

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

params = {
    "geometries": "geojson",
    "overview": "full",
    "steps": "true",
    "access_token": MAPBOX_TOKEN
}

col1, col2 = st.columns(2, gap="large")

# ── AS-IS 경로
with col1:
    st.markdown("#### 현재")
    try:
        m = Map(location=[asis_grp.geometry.y.mean(), asis_grp.geometry.x.mean()], zoom_start=12, tiles=COMMON_TILE)
        fg = FeatureGroup(name="ASIS")

        c_pts = asis_grp[asis_grp["location_t"] == "C"].reset_index()
        d_pts = asis_grp[asis_grp["location_t"] == "D"].reset_index()

        asis_total_duration_sec, asis_total_distance_km = 0, 0

        for idx, crow in c_pts.iterrows():
            color = palette[idx % len(palette)]
            c = crow.geometry
            d = d_pts.loc[d_pts.geometry.distance(c).idxmin()].geometry

            folium.map.Marker([c.y, c.x], icon=DivIcon(
                icon_size=(30,30), icon_anchor=(15,15),
                html=f'<div style="font-size:14px; color:#fff; background:{color}; border-radius:50%; width:30px; height:30px; text-align:center; line-height:30px;">{idx+1}</div>'
            )).add_to(fg)

            folium.Marker([d.y, d.x], icon=folium.Icon(icon="flag-checkered", prefix="fa", color=color)).add_to(fg)

            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{c.x},{c.y};{d.x},{d.y}"
            res = requests.get(url, params=params)
            data = res.json()
            routes = data.get("routes") or []

            if routes:
                asis_total_duration_sec += routes[0]["duration"]
                asis_total_distance_km += routes[0]["distance"] / 1000
                line = LineString(routes[0]["geometry"]["coordinates"])
                style = {"color": color, "weight": 5}
            else:
                line = LineString([(c.x, c.y), (d.x, d.y)])
                style = {"color": color, "weight": 3, "dashArray": "5,5"}

            GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        asis_cols[0].metric("ASIS 소요시간", f"{int(asis_total_duration_sec // 60)} 분")
        asis_cols[1].metric("ASIS 최단거리", f"{round(asis_total_distance_km, 2)} km")
        asis_cols[2].metric("ASIS 물류비", f"{int(asis_total_distance_km*5000):,} 원")
        asis_cols[3].metric("ASIS 탄소배출량", f"{round(asis_total_distance_km*0.65,2)} kg CO2")

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

# ── TO-BE 경로
with col2:
    st.markdown("#### 공동운송 도입 후")
    try:
        m = Map(location=[tobe_grp.geometry.y.mean(), tobe_grp.geometry.x.mean()], zoom_start=12, tiles=COMMON_TILE)
        fg = FeatureGroup(name="TOBE")

        c_pts = tobe_grp[tobe_grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
        d_pt = tobe_grp[tobe_grp["location_t"] == "D"].geometry.iloc[0]

        tobe_total_duration_sec, tobe_total_distance_km = 0, 0

        for i, row in c_pts.iterrows():
            folium.map.Marker([row.geometry.y, row.geometry.x], icon=DivIcon(
                icon_size=(30,30), icon_anchor=(15,15),
                html=f'<div style="font-size:14px; color:#fff; background:{palette[i % len(palette)]}; border-radius:50%; width:30px; height:30px; text-align:center; line-height:30px;">{i+1}</div>'
            )).add_to(fg)

        folium.Marker([d_pt.y, d_pt.x], icon=folium.Icon(icon="flag-checkered", prefix="fa", color=palette[-1])).add_to(fg)

        for i in range(len(c_pts)):
            start = c_pts.geometry.iloc[i]
            end = c_pts.geometry.iloc[i+1] if i < len(c_pts)-1 else d_pt

            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{start.x},{start.y};{end.x},{end.y}"
            res = requests.get(url, params=params).json()
            routes = res.get("routes") or []

            if routes:
                tobe_total_duration_sec += routes[0]["duration"]
                tobe_total_distance_km += routes[0]["distance"] / 1000
                coords = routes[0]["geometry"]["coordinates"]
                line = LineString(coords)
                style = {"color": palette[i % len(palette)], "weight": 5}
                GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        tobe_cols[0].metric("TOBE 소요시간", f"{int(tobe_total_duration_sec // 60)} 분")
        tobe_cols[1].metric("TOBE 최단거리", f"{round(tobe_total_distance_km, 2)} km")
        tobe_cols[2].metric("TOBE 물류비", f"{int(tobe_total_distance_km*5000):,} 원")
        tobe_cols[3].metric("TOBE 탄소배출량", f"{round(tobe_total_distance_km*0.65,2)} kg CO2")

        # 🔴 차이값 KPI (빨간색, 작은 글씨)
        diff_duration = int((asis_total_duration_sec - tobe_total_duration_sec) // 60)
        diff_distance = round(asis_total_distance_km - tobe_total_distance_km, 2)
        diff_cost     = int((asis_total_distance_km * 5000) - (tobe_total_distance_km * 5000))
        diff_emission = round((asis_total_distance_km * 0.65) - (tobe_total_distance_km * 0.65), 2)

        diff_cols = st.columns(4)
        diff_cols[0].markdown(
            f"<span style='color:red; font-size:12px;'>차이: {diff_duration} 분</span>",
            unsafe_allow_html=True
        )
        diff_cols[1].markdown(
            f"<span style='color:red; font-size:12px;'>차이: {diff_distance} km</span>",
            unsafe_allow_html=True
        )
        diff_cols[2].markdown(
            f"<span style='color:red; font-size:12px;'>차이: {diff_cost:,} 원</span>",
            unsafe_allow_html=True
        )
        diff_cols[3].markdown(
            f"<span style='color:red; font-size:12px;'>차이: {diff_emission} kg CO2</span>",
            unsafe_allow_html=True
        )

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
