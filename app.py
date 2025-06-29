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

# ─────────────────────────────
# 상단 로고 + 제목 배치
logo_col, title_col = st.columns([1, 8])

with logo_col:
    st.image("/image.jpg", width=80)  # 업로드된 이미지 경로에 맞춰주세요!

with title_col:
    st.markdown(
        "<h2 style='padding-top: 10px;'>DaTaSo, 지속가능한 축산물류를 위한 탄소저감형 가축운송 플랫폼</h2>",
        unsafe_allow_html=True
    )

# ─────────────────────────────
# 상수
MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_tobe_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"
COMMON_TILE = "CartoDB positron"

palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

# 데이터 로드
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("경로 선택 (sorting_id)", common_ids)

asis_grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
tobe_grp = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]

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

# ─────────────────────────────
# AS-IS 경로
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

        asis_cols[0].markdown(f"<h3 style='text-align: center;'>{int(asis_total_duration_sec // 60)} <span style='font-size:16px;'>분</span></h3><p style='text-align:center;'>ASIS 소요시간</p>", unsafe_allow_html=True)
        asis_cols[1].markdown(f"<h3 style='text-align: center;'>{round(asis_total_distance_km, 2)} <span style='font-size:16px;'>km</span></h3><p style='text-align:center;'>ASIS 최단거리</p>", unsafe_allow_html=True)
        asis_cols[2].markdown(f"<h3 style='text-align: center;'>{int(asis_total_distance_km*5000):,} <span style='font-size:16px;'>원</span></h3><p style='text-align:center;'>ASIS 물류비</p>", unsafe_allow_html=True)
        asis_cols[3].markdown(f"<h3 style='text-align: center;'>{round(asis_total_distance_km*0.65,2)} <span style='font-size:16px;'>kg CO2</span></h3><p style='text-align:center;'>ASIS 탄소배출량</p>", unsafe_allow_html=True)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

# ─────────────────────────────
# TO-BE 경로
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

        # 차이값 계산
        diff_duration = int((asis_total_duration_sec - tobe_total_duration_sec) // 60)
        diff_distance = round(asis_total_distance_km - tobe_total_distance_km, 2)
        diff_cost     = int((asis_total_distance_km * 5000) - (tobe_total_distance_km * 5000))
        diff_emission = round((asis_total_distance_km * 0.65) - (tobe_total_distance_km * 0.65), 2)

        # TO-BE KPI + 비교값 + 문구
        with tobe_cols[0]:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='font-size: 32px; font-weight: bold;'>{int(tobe_total_duration_sec // 60)}<span style='font-size: 18px;'> 분</span></div>
                    <div style='font-size: 14px; color: red; font-weight: bold;'>- {diff_duration} 분</div>
                    <div style='font-size: 14px; color: #666;'>TOBE 소요시간</div>
                </div>
            """, unsafe_allow_html=True)

        with tobe_cols[1]:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='font-size: 32px; font-weight: bold;'>{round(tobe_total_distance_km, 2)}<span style='font-size: 18px;'> km</span></div>
                    <div style='font-size: 14px; color: red; font-weight: bold;'>- {diff_distance} km</div>
                    <div style='font-size: 14px; color: #666;'>TOBE 최단거리</div>
                </div>
            """, unsafe_allow_html=True)

        with tobe_cols[2]:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='font-size: 32px; font-weight: bold;'>{int(tobe_total_distance_km*5000):,}<span style='font-size: 18px;'> 원</span></div>
                    <div style='font-size: 14px; color: red; font-weight: bold;'>- {diff_cost:,} 원</div>
                    <div style='font-size: 14px; color: #666;'>TOBE 물류비</div>
                </div>
            """, unsafe_allow_html=True)

        with tobe_cols[3]:
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div style='font-size: 32px; font-weight: bold;'>{round(tobe_total_distance_km*0.65,2)}<span style='font-size: 18px;'> kg CO2</span></div>
                    <div style='font-size: 14px; color: red; font-weight: bold;'>- {diff_emission} kg CO2</div>
                    <div style='font-size: 14px; color: #666;'>TOBE 탄소배출량</div>
                </div>
            """, unsafe_allow_html=True)

        fg.add_to(m)
        render_map(m)

    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
