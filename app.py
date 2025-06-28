import streamlit as st
import geopandas as gpd
import requests
from shapely.geometry import LineString
import folium
from folium import Map, FeatureGroup, GeoJson
from folium.plugins import BeautifyIcon
from streamlit.components.v1 import html

# 와이드 레이아웃
st.set_page_config(layout="wide")

MAPBOX_TOKEN = "pk.eyJ1Ijoia2lteWVvbmp1biIsImEiOiJjbWM5cTV2MXkxdnJ5MmlzM3N1dDVydWwxIn0.rAH4bQmtA-MmEuFwRLx32Q"
ASIS_PATH = "cb_asis_sample.shp"
TOBE_PATH = "cb_tobe_sample.shp"

# 컬러 팔레트
palette = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"
]

# KPI 영역
k1, k2, k3, k4 = st.columns(4)
k1.metric("ASIS 소요시간", "--", help="기존 경로의 예상 소요시간")
k2.metric("TOBE 소요시간", "--", help="개선 경로의 예상 소요시간")
k3.metric("물류비", "--", help="예상 물류비용")
k4.metric("탄소배출량", "--", help="예상 CO₂ 배출량")

st.markdown("---")  # 구분선

# 데이터 로드
gdf_asis = gpd.read_file(ASIS_PATH).to_crs(4326)
gdf_tobe = gpd.read_file(TOBE_PATH).to_crs(4326)

# 경로 선택
common_ids = sorted(set(gdf_asis["sorting_id"]) & set(gdf_tobe["sorting_id"]))
selected_id = st.selectbox("📌 경로 선택 (sorting_id)", common_ids)

def render_map(m, height=600):
    html(m.get_root().render(), height=height)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("#### ⬅ AS-IS 경로")
    try:
        grp = gdf_asis[gdf_asis["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"]
        d_pts = grp[grp["location_t"] == "D"]
        m = Map(
            location=[grp.geometry.y.mean(), grp.geometry.x.mean()],
            zoom_start=12,
            tiles="CartoDB positron",
            attr="CartoDB Positron"
        )
        fg = FeatureGroup(name=f"ASIS {selected_id}")

        for idx, (_, crow) in enumerate(c_pts.iterrows()):
            color = palette[idx % len(palette)]
            c = crow.geometry
            # 가장 가까운 D 찾기
            d_idx = d_pts.geometry.distance(c).idxmin()
            d = d_pts.loc[d_idx].geometry

            # 포인트 아이콘
            c_icon = BeautifyIcon(
                icon="truck", icon_shape="marker",
                background_color=color, border_color="#ffffff",
                text_color="#ffffff", number=idx+1
            )
            d_icon = BeautifyIcon(
                icon="industry", icon_shape="marker",
                background_color=color, border_color="#ffffff",
                text_color="#ffffff"
            )

            # 마커 추가
            folium.Marker(location=(c.y, c.x), icon=c_icon).add_to(fg)
            folium.Marker(location=(d.y, d.x), icon=d_icon).add_to(fg)

            # Mapbox 경로
            url = (
                f"https://api.mapbox.com/directions/v5/mapbox/driving/"
                f"{c.x},{c.y};{d.x},{d.y}"
            )
            res = requests.get(url, params={
                "geometries": "geojson",
                "overview": "simplified",
                "access_token": MAPBOX_TOKEN
            })
            res.raise_for_status()
            coords = res.json()["routes"][0]["geometry"]["coordinates"]
            line = LineString(coords)

            GeoJson(
                line,
                tooltip=f"C{idx+1} → D",
                style_function=lambda feat, col=color: {
                    "color": col, "weight": 5
                }
            ).add_to(fg)

        fg.add_to(m)
        render_map(m)
    except Exception as e:
        st.error(f"[ASIS 에러] {e}")

with col2:
    st.markdown("#### TO-BE ➡ 개선 경로")
    try:
        grp = gdf_tobe[gdf_tobe["sorting_id"] == selected_id]
        c_pts = grp[grp["location_t"] == "C"].sort_values("stop_seq", ascending=False)
        d_pt = grp[grp["location_t"] == "D"].iloc[0].geometry

        m = Map(
            location=[grp.geometry.y.mean(), grp.geometry.x.mean()],
            zoom_start=12,
            tiles="CartoDB dark_matter",
            attr="CartoDB Dark Matter"
        )
        fg = FeatureGroup(name=f"TOBE {selected_id}")

        coords = []
        for idx, (_, row) in enumerate(c_pts.iterrows()):
            color = palette[idx % len(palette)]
            pt = row.geometry
            coords.append((pt.y, pt.x))

            c_icon = BeautifyIcon(
                icon="map-pin", icon_shape="marker",
                background_color=color, border_color="#ffffff",
                text_color="#ffffff", number=row["stop_seq"]
            )
            folium.Marker(location=(pt.y, pt.x), icon=c_icon).add_to(fg)

        d_icon = BeautifyIcon(
            icon="flag-checkered", icon_shape="marker",
            background_color="#000000", border_color="#ffffff",
            text_color="#ffffff"
        )
        folium.Marker(location=(d_pt.y, d_pt.x), icon=d_icon).add_to(fg)

        # C→C & C→D 경로 (AS-IS와 완전히 동일한 스타일)
        for i in range(len(coords)):
            if i < len(coords) - 1:
                start, end = coords[i], coords[i+1]
                tooltip = f"C{c_pts.iloc[i]['stop_seq']} → C{c_pts.iloc[i+1]['stop_seq']}"
            else:
                start, end = coords[i], (d_pt.y, d_pt.x)
                tooltip = f"C{c_pts.iloc[i]['stop_seq']} → D"

            url = (
                f"https://api.mapbox.com/directions/v5/mapbox/driving/"
                f"{start[1]},{start[0]};{end[1]},{end[0]}"
            )
            res = requests.get(url, params={
                "geometries": "geojson",
                "overview": "simplified",
                "access_token": MAPBOX_TOKEN
            })
            res.raise_for_status()
            seg = LineString(res.json()["routes"][0]["geometry"]["coordinates"])

            # AS-IS와 동일하게 solid line, same weight
            GeoJson(
                seg,
                tooltip=tooltip,
                style_function=lambda feat, col=palette[i % len(palette)]: {
                    "color": col, "weight": 5
                }
            ).add_to(fg)

        fg.add_to(m)
        render_map(m)
    except Exception as e:
        st.error(f"[TOBE 에러] {e}")
