"""Simple Streamlit wrapper for querying OpenAlex institutions and visualizing RCA data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

OPENALEX_API_URL = "https://api.openalex.org/institutions"
OPENALEX_DEFAULT_PARAMS = {
    "page": 1,
    "sort": "relevance_score:desc",
    "per_page": 10,
    "mailto": "ui@openalex.org",
}
RCA_API_TEMPLATE = "https://gnt.place/institution_rca/{institution_id}"
BASE_DIR = Path(__file__).resolve().parent
SAMPLE_RESULTS_PATH = BASE_DIR / "sample.json"
SAMPLE_RCA_PATH = BASE_DIR / "sample_rca.json"


def _safe_read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _extract_id(full_id: str) -> str:
    # OpenAlex IDs are URIs; use the trailing segment.
    return full_id.rsplit("/", 1)[-1]


@st.cache_data(show_spinner=False)
def fetch_institutions(query: str) -> Dict[str, Any]:
    """Call OpenAlex and fallback to the bundled sample on failure."""
    params = {**OPENALEX_DEFAULT_PARAMS, "filter": f"default.search:{query}"}
    try:
        response = requests.get(OPENALEX_API_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return _safe_read_json(SAMPLE_RESULTS_PATH)


@st.cache_data(show_spinner=False)
def fetch_rca(institution_id: str) -> List[List[Any]]:
    """Fetch RCA data, temporarily falling back to the provided sample."""
    url = RCA_API_TEMPLATE.format(institution_id=institution_id)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return _safe_read_json(SAMPLE_RCA_PATH)


def render_results(results: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not results:
        st.info("該当する大学が見つかりませんでした。検索条件を変えてください。")
        return None

    summary_data = [
        {
            "名前": item.get("display_name"),
            "国": item.get("country_code"),
            "Works": item.get("works_count"),
            "Cited By": item.get("cited_by_count"),
            "ID": _extract_id(item.get("id", "")),
        }
        for item in results
    ]
    st.dataframe(summary_data, use_container_width=True, hide_index=True)

    label_to_item = {
        f"{entry['名前']} ({entry['国']})": entry for entry in summary_data
    }
    selected_label = st.selectbox("候補から大学を選択", list(label_to_item.keys()))
    return label_to_item[selected_label]


def _prepare_rca_dataframe(rca_rows: List[Any]) -> pd.DataFrame:
    if not rca_rows:
        return pd.DataFrame(columns=["discipline", "rca_citation", "rca_pub", "color"])

    first = rca_rows[0]
    if isinstance(first, dict):
        df = pd.DataFrame(rca_rows)
    else:
        df = pd.DataFrame(
            rca_rows,
            columns=["discipline", "rca_pub", "rca_citation", "color"][: len(first)],
        )

    if "rca_pub" not in df and "rca_paper" in df:
        df["rca_pub"] = df["rca_paper"]
    if "rca_citation" not in df and "publication" in df:
        df["rca_citation"] = df["publication"]
    if "color" not in df:
        df["color"] = "#1f77b4"

    df["rca_pub"] = pd.to_numeric(df["rca_pub"], errors="coerce")
    df["rca_citation"] = pd.to_numeric(df["rca_citation"], errors="coerce")
    df = df.dropna(subset=["rca_pub", "rca_citation"])

    return df[["discipline", "rca_citation", "rca_pub", "color"]]


def render_scatter(rca_rows: List[Any]) -> None:
    df = _prepare_rca_dataframe(rca_rows)
    if df.empty:
        st.warning("RCAデータが取得できませんでした。")
        return

    fig = go.Figure()
    for row in df.itertuples():
        fig.add_trace(
            go.Scatter(
                x=[row.rca_pub],
                y=[row.rca_citation],
                mode="markers+text",
                text=[row.discipline],
                textposition="top center",
                marker=dict(size=16, color=row.color, line=dict(width=1, color="#333")),
                hovertemplate=(
                    "<b>%{text}</b><br>RCA Pub: %{x}<br>RCA Citation: %{y}<extra></extra>"
                ),
            )
        )
    guide_line = dict(color="#888", dash="dash", width=2)
    fig.add_hline(y=1, line=guide_line)
    fig.add_vline(x=1, line=guide_line)

    x_min, x_max = df["rca_pub"].min(), df["rca_pub"].max()
    y_min, y_max = df["rca_citation"].min(), df["rca_citation"].max()
    x_span = x_max - x_min if x_max != x_min else 0.5
    y_span = y_max - y_min if y_max != y_min else 0.5
    x_padding = max(0.1, x_span * 0.15)
    y_padding = max(0.1, y_span * 0.15)

    fig.update_layout(
        xaxis_title="RCA (pub)",
        yaxis_title="RCA (citation)",
        xaxis=dict(zeroline=False, range=[x_min - x_padding, x_max + x_padding]),
        yaxis=dict(zeroline=False, range=[y_min - y_padding, y_max + y_padding]),
        template="plotly_white",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)


st.set_page_config(page_title="UniRCAVis", layout="wide")
st.title("大学分野別強みビジュアライザー")
st.caption("OpenAlexとgnt.place APIを利用した大学の強み分析デモ")

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

with st.form("institution_search", clear_on_submit=False):
    query = st.text_input("大学名", value="東京大学", placeholder="大学名を入力...")
    submitted = st.form_submit_button("検索")

if submitted:
    cleaned = query.strip()
    if cleaned:
        with st.spinner("大学候補を取得中..."):
            response_json = fetch_institutions(cleaned)
        st.session_state["search_results"] = response_json.get("results", [])
    else:
        st.warning("大学名を入力してください。")

results = st.session_state.get("search_results", [])
selected = render_results(results)

if selected:
    institution_id = selected["ID"]
    st.markdown(f"### 強み分析 (Institution ID: `{institution_id}`)")
    with st.spinner("強み分析データを取得中..."):
        rca_data = fetch_rca(institution_id)
    render_scatter(rca_data)
elif not results:
    st.info("大学名を入力して検索を開始してください。")
