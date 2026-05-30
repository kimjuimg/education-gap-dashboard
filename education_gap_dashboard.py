"""
지역별 교육격차 현황 분석 대시보드 v2
제8회 교육공공데이터 AI 활용대회 출품용
- KESS 실데이터 구조 반영 (샘플 → CSV 교체 가능)
- 지도 시각화 (choropleth)
- 연도별 추이 그래프 추가
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

st.set_page_config(page_title="지역별 교육격차 분석 v2", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; }
    h1 { font-size: 1.6rem !important; }
    .stMetric label { font-size: 0.8rem !important; }
    .stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 ───────────────────────────────────────────────────
# ※ 실제 사용 시: pd.read_csv("kess_data.csv") 로 교체
@st.cache_data
def load_data():
    regions = ["서울","경기","인천","부산","대구","광주","대전","울산","세종","경남","경북","전남","전북","충남","충북","강원","제주"]
    region_type = ["수도권","수도권","수도권","영남권","영남권","호남권","충청권","영남권","충청권","영남권","영남권","호남권","호남권","충청권","충청권","강원·제주","강원·제주"]

    # 연도별 데이터 (2019~2023)
    years = [2019, 2020, 2021, 2022, 2023]
    rows = []
    base_teacher   = [11.2,12.1,13.0,13.4,13.8,14.1,13.6,14.0,12.8,15.1,16.4,15.9,15.3,15.6,14.9,17.4,14.2]
    base_achieve   = [82.3,79.1,76.8,73.2,72.4,70.1,75.3,73.0,85.2,68.4,65.4,63.9,66.1,64.7,67.2,62.1,71.4]
    base_tutoring  = [62,54,46,35,33,28,38,32,44,27,22,20,21,24,26,18,30]
    base_after     = [72.1,68.4,65.2,63.5,62.8,61.4,64.3,60.9,67.2,58.4,54.1,52.3,55.6,53.8,56.2,48.9,59.7]
    base_temp      = [18.2,20.1,22.4,21.8,23.2,24.5,21.3,22.9,19.4,25.6,27.3,28.9,26.7,27.1,25.8,30.2,23.6]

    import random
    random.seed(42)
    for i, region in enumerate(regions):
        for y_idx, year in enumerate(years):
            noise = lambda base, scale=0.03: round(base * (1 + random.uniform(-scale, scale) * (y_idx+1)), 1)
            rows.append({
                "지역": region, "권역": region_type[i], "연도": year,
                "교원1인당학생수": noise(base_teacher[i]),
                "보통학력이상비율": min(99, noise(base_achieve[i], 0.04)),
                "월사교육비": noise(base_tutoring[i], 0.05),
                "방과후참여율": noise(base_after[i], 0.03),
                "기간제교원비율": noise(base_temp[i], 0.04),
            })

    df = pd.DataFrame(rows)
    df["격차지수"] = (
        (1-(df["교원1인당학생수"]-df["교원1인당학생수"].min())/(df["교원1인당학생수"].max()-df["교원1인당학생수"].min()))*0.3 +
        (df["보통학력이상비율"]-df["보통학력이상비율"].min())/(df["보통학력이상비율"].max()-df["보통학력이상비율"].min())*0.3 +
        (df["방과후참여율"]-df["방과후참여율"].min())/(df["방과후참여율"].max()-df["방과후참여율"].min())*0.2 +
        (1-(df["기간제교원비율"]-df["기간제교원비율"].min())/(df["기간제교원비율"].max()-df["기간제교원비율"].min()))*0.2
    )*100
    return df

# 한국 시도 GeoJSON (간략화 좌표 - 실제 제출 시 공식 GeoJSON 사용 권장)
@st.cache_data
def load_geojson():
    geo = {
        "type": "FeatureCollection",
        "features": [
            {"type":"Feature","properties":{"name":"서울"},"geometry":{"type":"Polygon","coordinates":[[[126.75,37.42],[127.18,37.42],[127.18,37.70],[126.75,37.70],[126.75,37.42]]]}},
            {"type":"Feature","properties":{"name":"경기"},"geometry":{"type":"Polygon","coordinates":[[[126.42,36.98],[127.82,36.98],[127.82,38.30],[126.42,38.30],[126.42,36.98]]]}},
            {"type":"Feature","properties":{"name":"인천"},"geometry":{"type":"Polygon","coordinates":[[[126.30,37.25],[126.78,37.25],[126.78,37.68],[126.30,37.68],[126.30,37.25]]]}},
            {"type":"Feature","properties":{"name":"강원"},"geometry":{"type":"Polygon","coordinates":[[[127.72,37.04],[129.37,37.04],[129.37,38.62],[127.72,38.62],[127.72,37.04]]]}},
            {"type":"Feature","properties":{"name":"충북"},"geometry":{"type":"Polygon","coordinates":[[[127.30,36.35],[128.52,36.35],[128.52,37.28],[127.30,37.28],[127.30,36.35]]]}},
            {"type":"Feature","properties":{"name":"충남"},"geometry":{"type":"Polygon","coordinates":[[[126.10,36.10],[127.40,36.10],[127.40,37.10],[126.10,37.10],[126.10,36.10]]]}},
            {"type":"Feature","properties":{"name":"대전"},"geometry":{"type":"Polygon","coordinates":[[[127.30,36.20],[127.55,36.20],[127.55,36.48],[127.30,36.48],[127.30,36.20]]]}},
            {"type":"Feature","properties":{"name":"세종"},"geometry":{"type":"Polygon","coordinates":[[[127.18,36.40],[127.40,36.40],[127.40,36.65],[127.18,36.65],[127.18,36.40]]]}},
            {"type":"Feature","properties":{"name":"경북"},"geometry":{"type":"Polygon","coordinates":[[[128.22,35.72],[129.40,35.72],[129.40,37.12],[128.22,37.12],[128.22,35.72]]]}},
            {"type":"Feature","properties":{"name":"대구"},"geometry":{"type":"Polygon","coordinates":[[[128.45,35.78],[128.75,35.78],[128.75,36.02],[128.45,36.02],[128.45,35.78]]]}},
            {"type":"Feature","properties":{"name":"울산"},"geometry":{"type":"Polygon","coordinates":[[[129.00,35.40],[129.38,35.40],[129.38,35.75],[129.00,35.75],[129.00,35.40]]]}},
            {"type":"Feature","properties":{"name":"부산"},"geometry":{"type":"Polygon","coordinates":[[[128.78,35.02],[129.32,35.02],[129.32,35.42],[128.78,35.42],[128.78,35.02]]]}},
            {"type":"Feature","properties":{"name":"경남"},"geometry":{"type":"Polygon","coordinates":[[[127.68,34.68],[129.20,34.68],[129.20,35.72],[127.68,35.72],[127.68,34.68]]]}},
            {"type":"Feature","properties":{"name":"전북"},"geometry":{"type":"Polygon","coordinates":[[[126.38,35.48],[127.88,35.48],[127.88,36.28],[126.38,36.28],[126.38,35.48]]]}},
            {"type":"Feature","properties":{"name":"광주"},"geometry":{"type":"Polygon","coordinates":[[[126.72,35.02],[126.98,35.02],[126.98,35.28],[126.72,35.28],[126.72,35.02]]]}},
            {"type":"Feature","properties":{"name":"전남"},"geometry":{"type":"Polygon","coordinates":[[[125.98,34.18],[127.78,34.18],[127.78,35.48],[125.98,35.48],[125.98,34.18]]]}},
            {"type":"Feature","properties":{"name":"제주"},"geometry":{"type":"Polygon","coordinates":[[[126.12,33.18],[126.98,33.18],[126.98,33.62],[126.12,33.62],[126.12,33.18]]]}},
        ]
    }
    return geo

df_all = load_data()
geojson = load_geojson()

# ── 사이드바 ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 필터")
    selected_year = st.selectbox("기준 연도", [2023,2022,2021,2020,2019], index=0)
    selected_regions = st.multiselect("권역 선택", options=df_all["권역"].unique().tolist(), default=df_all["권역"].unique().tolist())
    school_level = st.radio("학교급", ["중학교","고등학교","초등학교"], index=0)
    st.markdown("---")
    st.caption("📌 데이터 출처")
    st.caption("- 교육통계서비스(KESS)")
    st.caption("- 통계청 사교육비 조사")
    st.caption("- 교육부 학업성취도 평가")
    st.markdown("---")
    st.info("💡 실제 데이터 교체 방법\n\nkess_data.csv 파일을\n같은 폴더에 넣고\nload_data() 상단 주석 참고")

df_year = df_all[df_all["연도"]==selected_year]
filtered = df_year[df_year["권역"].isin(selected_regions)]
color_map = {"수도권":"#1a56db","영남권":"#0e9f6e","호남권":"#e3a008","충청권":"#7e3af2","강원·제주":"#e74694"}

# ── 타이틀 ───────────────────────────────────────────────────────
st.title("📊 지역별 교육격차 현황 분석")
st.caption(f"{selected_year}년 기준 · {school_level} · 시도별 교육 인프라·성취도·사교육비 종합 현황")

# ── KPI ──────────────────────────────────────────────────────────
c1,c2,c3,c4 = st.columns(4)
c1.metric("교원 1인당 학생 수 최대격차", f"{filtered['교원1인당학생수'].max()-filtered['교원1인당학생수'].min():.1f}명", "수도권↔비수도권", delta_color="inverse")
c2.metric("학업성취도 최대격차", f"{filtered['보통학력이상비율'].max()-filtered['보통학력이상비율'].min():.1f}%p", "비율 격차", delta_color="inverse")
c3.metric("월 사교육비 최대격차", f"{filtered['월사교육비'].max()-filtered['월사교육비'].min():.0f}만원", "서울↔강원", delta_color="inverse")
c4.metric("방과후 참여율 최대격차", f"{filtered['방과후참여율'].max()-filtered['방과후참여율'].min():.1f}%p", "접근성 차이", delta_color="inverse")

st.markdown("---")

# ── 탭 구성 ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 현황 분석", "🗺️ 지도 시각화", "📈 연도별 추이", "📋 원본 데이터"])

# ════════════════════════════════════════════════════════════════
# TAB 1: 현황 분석
# ════════════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("교원 1인당 학생 수")
        fig1 = px.bar(filtered.sort_values("교원1인당학생수"), x="교원1인당학생수", y="지역",
                      color="권역", orientation="h", color_discrete_map=color_map,
                      labels={"교원1인당학생수":"학생 수 (명)","지역":""}, height=400)
        fig1.update_layout(margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("보통학력 이상 비율 (%)")
        fig2 = px.bar(filtered.sort_values("보통학력이상비율"), x="보통학력이상비율", y="지역",
                      color="권역", orientation="h", color_discrete_map=color_map,
                      labels={"보통학력이상비율":"비율 (%)","지역":""}, height=400)
        fig2.update_layout(margin=dict(l=10,r=10,t=10,b=10), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("사교육비 지출 vs 학업성취도")
    fig3 = px.scatter(filtered, x="월사교육비", y="보통학력이상비율",
                      color="권역", size="방과후참여율", text="지역",
                      color_discrete_map=color_map,
                      labels={"월사교육비":"월평균 사교육비 (만원)","보통학력이상비율":"보통학력 이상 비율 (%)"},
                      trendline="ols", height=420)
    fig3.update_traces(textposition="top center", marker=dict(opacity=0.85))
    fig3.update_layout(margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("버블 크기 = 방과후학교 참여율 · 추세선 = OLS 회귀선")

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("종합 격차 지수")
        st.caption("높을수록 교육 여건 양호")
        fig4 = px.bar(filtered.sort_values("격차지수", ascending=False),
                      x="지역", y="격차지수", color="격차지수",
                      color_continuous_scale="Blues",
                      labels={"격차지수":"종합 지수","지역":""}, height=320)
        fig4.update_layout(margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

    with col4:
        st.subheader("권역별 레이더 비교")
        radar_df = filtered.groupby("권역").mean(numeric_only=True).reset_index()
        for col in ["교원1인당학생수","보통학력이상비율","월사교육비","방과후참여율","기간제교원비율"]:
            mn,mx = df_all[col].min(), df_all[col].max()
            if col in ["교원1인당학생수","기간제교원비율"]:
                radar_df[col] = (1-(radar_df[col]-mn)/(mx-mn))*100
            else:
                radar_df[col] = (radar_df[col]-mn)/(mx-mn)*100
        cats = ["교원 인프라","학업성취도","사교육비(역산)","방과후 접근성","정규교원(역산)"]
        fig5 = go.Figure()
        for _, row in radar_df.iterrows():
            vals = [row["교원1인당학생수"],row["보통학력이상비율"],row["월사교육비"],row["방과후참여율"],row["기간제교원비율"]]
            fig5.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]],
                fill="toself", name=row["권역"],
                line_color=color_map.get(row["권역"],"#888"), opacity=0.7))
        fig5.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),
                           height=320, margin=dict(l=50,r=50,t=20,b=20))
        st.plotly_chart(fig5, use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 2: 지도 시각화
# ════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🗺️ 시도별 교육격차 지도")

    map_metric = st.selectbox("지도에 표시할 지표", [
        "격차지수", "보통학력이상비율", "교원1인당학생수", "월사교육비", "방과후참여율", "기간제교원비율"
    ])

    label_map = {
        "격차지수": "종합 격차 지수 (높을수록 양호)",
        "보통학력이상비율": "보통학력 이상 비율 (%)",
        "교원1인당학생수": "교원 1인당 학생 수 (명)",
        "월사교육비": "월평균 사교육비 (만원)",
        "방과후참여율": "방과후 참여율 (%)",
        "기간제교원비율": "기간제 교원 비율 (%)",
    }

    # 역방향 색상 지표 (낮을수록 좋음)
    reverse = map_metric in ["교원1인당학생수","기간제교원비율","월사교육비"]
    cscale = "RdYlGn_r" if reverse else "RdYlGn"

    map_df = df_year[["지역", map_metric]].copy()

    fig_map = px.choropleth_mapbox(
        map_df,
        geojson=geojson,
        locations="지역",
        featureidkey="properties.name",
        color=map_metric,
        color_continuous_scale=cscale,
        mapbox_style="carto-positron",
        zoom=5.8,
        center={"lat": 36.5, "lon": 127.8},
        opacity=0.75,
        labels={map_metric: label_map[map_metric]},
        hover_name="지역",
        hover_data={map_metric: ":.1f"},
        height=550,
    )
    fig_map.update_layout(margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_map, use_container_width=True)

    if reverse:
        st.caption(f"🔴 빨간색 = {map_metric} 높음(불리) · 🟢 초록색 = 낮음(유리)")
    else:
        st.caption(f"🟢 초록색 = {map_metric} 높음(유리) · 🔴 빨간색 = 낮음(불리)")

    # 순위표
    st.subheader(f"{map_metric} 시도 순위")
    rank_df = df_year[["지역","권역",map_metric]].sort_values(map_metric, ascending=reverse).reset_index(drop=True)
    rank_df.index += 1
    rank_df.columns = ["지역","권역",label_map[map_metric]]
    st.dataframe(rank_df, use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 3: 연도별 추이
# ════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📈 연도별 추이 분석 (2019~2023)")

    trend_metric = st.selectbox("지표 선택", [
        "보통학력이상비율","교원1인당학생수","월사교육비","방과후참여율","기간제교원비율","격차지수"
    ], key="trend")

    trend_type = st.radio("보기 방식", ["지역별","권역별 평균"], horizontal=True)

    trend_df = df_all[df_all["권역"].isin(selected_regions)]

    if trend_type == "지역별":
        selected_areas = st.multiselect(
            "지역 선택 (최대 6개)",
            options=trend_df["지역"].unique().tolist(),
            default=["서울","경기","강원","전남","세종","부산"]
        )
        plot_df = trend_df[trend_df["지역"].isin(selected_areas)]
        fig_trend = px.line(plot_df, x="연도", y=trend_metric, color="지역",
                            markers=True, height=420,
                            labels={"연도":"연도", trend_metric: trend_metric},
                            title=f"지역별 {trend_metric} 추이")
    else:
        agg_df = trend_df.groupby(["연도","권역"])[trend_metric].mean().reset_index()
        fig_trend = px.line(agg_df, x="연도", y=trend_metric, color="권역",
                            color_discrete_map=color_map,
                            markers=True, height=420,
                            labels={"연도":"연도", trend_metric: trend_metric},
                            title=f"권역별 {trend_metric} 평균 추이")

    fig_trend.update_traces(line=dict(width=2.5), marker=dict(size=8))
    fig_trend.update_layout(margin=dict(l=10,r=10,t=40,b=10),
                            xaxis=dict(tickmode="linear", dtick=1))
    st.plotly_chart(fig_trend, use_container_width=True)

    # 격차 추이 (최대-최소)
    st.subheader("수도권 vs 비수도권 격차 추이")
    gap_metro = df_all[df_all["권역"]=="수도권"].groupby("연도")[trend_metric].mean()
    gap_non   = df_all[df_all["권역"]!="수도권"].groupby("연도")[trend_metric].mean()
    gap_df = pd.DataFrame({
        "수도권 평균": gap_metro,
        "비수도권 평균": gap_non,
        "격차": (gap_metro - gap_non).abs()
    }).reset_index()

    fig_gap = go.Figure()
    fig_gap.add_trace(go.Scatter(x=gap_df["연도"], y=gap_df["수도권 평균"], name="수도권 평균",
                                  line=dict(color="#1a56db", width=2.5), mode="lines+markers"))
    fig_gap.add_trace(go.Scatter(x=gap_df["연도"], y=gap_df["비수도권 평균"], name="비수도권 평균",
                                  line=dict(color="#e3a008", width=2.5), mode="lines+markers"))
    fig_gap.add_trace(go.Bar(x=gap_df["연도"], y=gap_df["격차"], name="절대 격차",
                              marker_color="rgba(220,50,50,0.25)", yaxis="y2"))
    fig_gap.update_layout(
        height=380,
        margin=dict(l=10,r=10,t=20,b=10),
        xaxis=dict(tickmode="linear", dtick=1),
        yaxis=dict(title=trend_metric),
        yaxis2=dict(title="격차", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.08),
        hovermode="x unified"
    )
    st.plotly_chart(fig_gap, use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 4: 원본 데이터
# ════════════════════════════════════════════════════════════════
with tab4:
    st.subheader(f"원본 데이터 ({selected_year}년)")
    st.caption("※ KESS 실데이터 교체 시 load_data() 함수 상단 주석 참고")

    show_all = st.checkbox("전체 연도 보기", value=False)
    display_df = df_all[df_all["권역"].isin(selected_regions)] if show_all else filtered

    st.dataframe(
        display_df.style.background_gradient(subset=["격차지수"], cmap="Blues"),
        use_container_width=True
    )
    st.download_button(
        "📥 CSV 다운로드",
        data=display_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name=f"education_gap_{selected_year}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("⚠️ 현재 샘플(가상) 데이터 기반 프로토타입 · 실제 제출 시 KESS·통계청 공공데이터로 교체 필요")