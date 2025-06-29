import streamlit as st
import geopandas as gpd
import requests
import base64
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, GeoJson
from folium.features import DivIcon
from streamlit.components.v1 import html

# ───────────── 와이드 레이아웃 ─────────────
st.set_page_config(layout="wide")

# ───────────── Base64 이미지 인코딩 ─────────────
file_path = "./image.jpg"
with open(file_path, "rb") as f:
    img_bytes = f.read()
encoded = base64.b64encode(img_bytes).decode()

# ───────────── 상단 로고 + 제목 ─────────────
st.markdown(
    f"""
    <div style='display: flex; align-items: center; justify-content: center; margin-bottom: 15px;'>
        <img src="data:image/png;base64,{encoded}" style='width: 180px; margin-right: 20px;'/>
        <h2 style='margin: 0; color: #333; text-align: center;'>
            지속가능한 축산물류를 위한 탄소저감형 가축운송 플랫폼
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

# ───────────── 상수 ─────────────
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_tobe_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"
COMMON_TILE = "CartoDB positron"
palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

# ───────────── 데이터 로드 ─────────────
gdf_current = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_dataso = gpd.read_file(TOBE_PATH).to_crs(4326)

common_ids = sorted(set(gdf_current["sorting_id"]) & set(gdf_dataso["sorting_id"]))
selected_id = st.selectbox("농가 선택", common_ids)

current_grp = gdf_current[gdf_current["sorting_id"] == selected_id]
dataso_grp = gdf_dataso[gdf_dataso["sorting_id"] == selected_id]

current_cols = st.columns(4)
dataso_cols = st.columns(4)

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

# ───────────── 현재 경로 ─────────────
with col1:
    st.markdown("#### 현재")
    try:
        m = Map(
            location=[current_grp.geometry.y.mean(), current_grp.geometry.x.mean()],
            zoom_start=9,  # 👈 한 단계 줌 아웃
            tiles=COMMON_TILE
        )
        fg = FeatureGroup(name="현재")

        c_pts = current_grp[current_grp["location_t"] == "C"].reset_index()
        d_pts = current_grp[current_grp["location_t"] == "D"].reset_index()

        current_total_duration_sec, current_total_distance_km = 0, 0

        for idx, crow in c_pts.iterrows():
            color = palette[idx % len(palette)]
            c = crow.geometry
            d = d_pts.loc[d_pts.geometry.distance(c).idxmin()].geometry

            # 농가 (C)
            folium.Marker([c.y, c.x], icon=DivIcon(
                icon_size=(30,30), icon_anchor=(15,15),
                html=f'<div style="font-size:14px; color:#fff; background:{color}; border-radius:50%; width:30px; height:30px; text-align:center; line-height:30px;">{idx+1}</div>'
            )).add_to(fg)

            # 도축장 (D)
            folium.Marker([d.y, d.x], icon=folium.Icon(icon="industry", prefix="fa", color="black")).add_to(fg)

            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{c.x},{c.y};{d.x},{d.y}"
            res = requests.get(url, params=params)
            data = res.json()
            routes = data.get("routes") or []

            if routes:
                current_total_duration_sec += routes[0]["duration"]
                current_total_distance_km += routes[0]["distance"] / 1000
                line = LineString(routes[0]["geometry"]["coordinates"])
                style = {"color": color, "weight": 5}
            else:
                line = LineString([(c.x, c.y), (d.x, d.y)])
                style = {"color": color, "weight": 3, "dashArray": "5,5"}

            GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        # ───────────── 범례 (농가/도축장) ─────────────
        legend_html = f"""
        <div style="
            position: fixed;
            bottom: 50px; left: 50px; width: 200px; height: auto;
            border:2px solid grey; z-index:9999; font-size:14px;
            background-color:white; padding: 10px;">
            <b>범례</b><br>
            <i style="background:{palette[0]};width:20px;height:20px;float:left;margin-right:5px; border-radius:50%;"></i> 농가 (C)<br>
            <i class="fa fa-industry" style="color:black;margin-right:5px;"></i> 도축장 (D)
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        fg.add_to(m)

        # KPI 출력
        current_cols[0].markdown(f"<div style='text-align:center;'>현재 소요시간<br><span style='font-size:32px;'>{int(current_total_duration_sec // 60)} 분</span></div>", unsafe_allow_html=True)
        current_cols[1].markdown(f"<div style='text-align:center;'>현재 최단거리<br><span style='font-size:32px;'>{round(current_total_distance_km,2)} km</span></div>", unsafe_allow_html=True)
        current_cols[2].markdown(f"<div style='text-align:center;'>현재 물류비<br><span style='font-size:32px;'>{int(current_total_distance_km*5000):,} 원</span></div>", unsafe_allow_html=True)
        current_cols[3].markdown(f"<div style='text-align:center;'>현재 탄소배출량<br><span style='font-size:32px;'>{round(current_total_distance_km*0.65,2)} kg CO2</span></div>", unsafe_allow_html=True)

        render_map(m)

    except Exception as e:
        st.error(f"[현재 에러] {e}")

# ───────────── 다타소(DaTaSo) 도입 후 ─────────────
with col2:
    st.markdown("#### 다타소(DaTaSo) 도입 후")
    try:
        m = Map(
            location=[dataso_grp.geometry.y.mean(), dataso_grp.geometry.x.mean()],
            zoom_start=9,  # 👈 한 단계 줌 아웃
            tiles=COMMON_TILE
        )
        fg = FeatureGroup(name="다타소")

        c_pts = dataso_grp[dataso_grp["location_t"] == "C"].sort_values("stop_seq").reset_index()
        d_pt = dataso_grp[dataso_grp["location_t"] == "D"].geometry.iloc[0]

        dataso_total_duration_sec, dataso_total_distance_km = 0, 0

        for i, row in c_pts.iterrows():
            folium.Marker([row.geometry.y, row.geometry.x], icon=DivIcon(
                icon_size=(30,30), icon_anchor=(15,15),
                html=f'<div style="font-size:14px; color:#fff; background:{palette[i % len(palette)]}; border-radius:50%; width:30px; height:30px; text-align:center; line-height:30px;">{i+1}</div>'
            )).add_to(fg)

        folium.Marker([d_pt.y, d_pt.x], icon=folium.Icon(icon="industry", prefix="fa", color="black")).add_to(fg)

        for i in range(len(c_pts)):
            start = c_pts.geometry.iloc[i]
            end = c_pts.geometry.iloc[i+1] if i < len(c_pts)-1 else d_pt

            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{start.x},{start.y};{end.x},{end.y}"
            res = requests.get(url, params=params).json()
            routes = res.get("routes") or []

            if routes:
                dataso_total_duration_sec += routes[0]["duration"]
                dataso_total_distance_km += routes[0]["distance"] / 1000
                coords = routes[0]["geometry"]["coordinates"]
                line = LineString(coords)
                style = {"color": palette[i % len(palette)], "weight": 5}
                GeoJson(line, style_function=lambda _, s=style: s).add_to(fg)

        m.get_root().html.add_child(folium.Element(legend_html))

        fg.add_to(m)

        dataso_cols[0].markdown(f"<div style='text-align:center;'>다타소 소요시간<br><span style='font-size:32px;'>{int(dataso_total_duration_sec // 60)} 분</span></div>", unsafe_allow_html=True)
        dataso_cols[1].markdown(f"<div style='text-align:center;'>다타소 최단거리<br><span style='font-size:32px;'>{round(dataso_total_distance_km,2)} km</span></div>", unsafe_allow_html=True)
        dataso_cols[2].markdown(f"<div style='text-align:center;'>다타소 물류비<br><span style='font-size:32px;'>{int(dataso_total_distance_km*5000):,} 원</span></div>", unsafe_allow_html=True)
        dataso_cols[3].markdown(f"<div style='text-align:center;'>다타소 탄소배출량<br><span style='font-size:32px;'>{round(dataso_total_distance_km*0.65,2)} kg CO2</span></div>", unsafe_allow_html=True)

        render_map(m)

    except Exception as e:
        st.error(f"[다타소 에러] {e}")
