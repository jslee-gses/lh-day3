from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="출동거리 증가율 대시보드",
    page_icon="🚒",
    layout="wide",
)

DATA_PATH = Path(__file__).with_name("count_merged.csv")
REQUIRED_COLUMNS = {
    "fire_station_name",
    "출동거리_2020",
    "출동거리_2021",
}


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """CSV를 읽고 2020년 대비 2021년 출동거리 증가율을 계산한다."""
    data = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"필수 컬럼이 없습니다: {missing_text}")

    if (data["출동거리_2020"] <= 0).any():
        raise ValueError("출동거리_2020에는 0보다 큰 값만 있어야 합니다.")

    data["출동거리_증가율"] = (
        (data["출동거리_2021"] - data["출동거리_2020"])
        / data["출동거리_2020"]
        * 100
    )
    return data


def build_bar_chart(data: pd.DataFrame) -> go.Figure:
    """증가율을 내림차순으로 정렬한 가로 막대그래프를 만든다."""
    chart_data = data.sort_values("출동거리_증가율", ascending=False).reset_index(drop=True)

    colors = []
    for rank, value in enumerate(chart_data["출동거리_증가율"]):
        if rank < 5:
            colors.append("#D84A3A")  # 상위 5개
        elif value < 0:
            colors.append("#3568A8")  # 음수
        else:
            colors.append("#E58B2A")  # 양수

    fig = go.Figure(
        go.Bar(
            x=chart_data["출동거리_증가율"],
            y=chart_data["fire_station_name"],
            orientation="h",
            marker={"color": colors, "line": {"color": "#6B3B28", "width": 0.6}},
            text=chart_data["출동거리_증가율"].map(lambda value: f"{value:+.1f}%"),
            textposition="outside",
            customdata=chart_data[["출동거리_2020", "출동거리_2021"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "2020년 출동거리: %{customdata[0]:.3f}<br>"
                "2021년 출동거리: %{customdata[1]:.3f}<br>"
                "증가율: %{x:+.2f}%<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="소방서별 출동거리 증가율",
        xaxis_title="증가율(%)",
        yaxis_title=None,
        height=max(560, len(chart_data) * 29),
        margin={"l": 120, "r": 75, "t": 60, "b": 55},
        template="plotly_white",
        showlegend=False,
        font={"family": "Malgun Gothic, Arial, sans-serif", "color": "#222831"},
    )
    fig.update_xaxes(
        zeroline=True,
        zerolinecolor="#40464D",
        zerolinewidth=1.2,
        gridcolor="#E6E9ED",
        ticksuffix="%",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


st.title("🚒 2020년 대비 2021년 출동거리 증가율")
st.caption("증가율 = (2021년 출동거리 − 2020년 출동거리) ÷ 2020년 출동거리 × 100")

try:
    df = load_data(DATA_PATH)
except FileNotFoundError:
    st.error("count_merged.csv 파일을 app.py와 같은 폴더에 넣어 주세요.")
    st.stop()
except (ValueError, pd.errors.ParserError) as exc:
    st.error(f"데이터를 불러오지 못했습니다: {exc}")
    st.stop()

with st.sidebar:
    st.header("필터")
    station_options = df["fire_station_name"].tolist()
    selected_stations = st.multiselect(
        "소방서 선택",
        options=station_options,
        default=station_options,
    )

filtered_df = df[df["fire_station_name"].isin(selected_stations)].copy()

if filtered_df.empty:
    st.warning("표시할 소방서를 하나 이상 선택해 주세요.")
    st.stop()

max_row = filtered_df.loc[filtered_df["출동거리_증가율"].idxmax()]
min_row = filtered_df.loc[filtered_df["출동거리_증가율"].idxmin()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("선택 소방서", f"{len(filtered_df)}개")
col2.metric("평균 증가율", f"{filtered_df['출동거리_증가율'].mean():.1f}%")
col3.metric("최고 증가율", f"{max_row['출동거리_증가율']:.1f}%", max_row["fire_station_name"])
col4.metric("최저 증가율", f"{min_row['출동거리_증가율']:.1f}%", min_row["fire_station_name"])

st.plotly_chart(build_bar_chart(filtered_df), width="stretch")
st.caption("색상: 빨강 = 선택 항목 중 증가율 상위 5개, 오렌지 = 양수, 파랑 = 음수")

st.subheader("상세 데이터")
display_df = (
    filtered_df[
        ["fire_station_name", "출동거리_2020", "출동거리_2021", "출동거리_증가율"]
    ]
    .sort_values("출동거리_증가율", ascending=False)
    .rename(
        columns={
            "fire_station_name": "소방서",
            "출동거리_2020": "2020년 출동거리",
            "출동거리_2021": "2021년 출동거리",
            "출동거리_증가율": "증가율(%)",
        }
    )
)
st.dataframe(
    display_df.style.format(
        {
            "2020년 출동거리": "{:.3f}",
            "2021년 출동거리": "{:.3f}",
            "증가율(%)": "{:.2f}",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.download_button(
    "필터링 결과 CSV 다운로드",
    data=display_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="dispatch_distance_growth.csv",
    mime="text/csv",
)

with st.expander("데이터 출처 및 계산 기준"):
    st.write("데이터 파일: `count_merged.csv`")
    st.write("관측 단위: 소방서")
    st.write("비교 기간: 2020년과 2021년")


