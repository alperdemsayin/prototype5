"""User-friendly Streamlit dashboard for maritime routing optimization."""

import json
import math
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from structures import Plant, Ship
from solver import quick_diagnostics, run_solver


st.set_page_config(
    page_title="Maritime Optimizer",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Maritime Inventory Routing Optimizer"
APP_SUBTITLE = (
    "Simple decision support dashboard for route planning, plant monitoring, and cost analysis"
)

FIXED_SCENARIO = {
    "depot": {"name": "Istanbul Depot", "lat": 41.0082, "lon": 28.9784},
    "plants": [
        {"name": "Antalya", "lat": 36.8969, "lon": 30.7133, "cap": 500.0, "init_stock": 400.0, "cons_rate": 5.0, "deadline": 120.0},
        {"name": "Iskenderun", "lat": 36.5872, "lon": 36.1735, "cap": 420.0, "init_stock": 330.0, "cons_rate": 4.0, "deadline": 110.0},
        {"name": "Mersin", "lat": 36.8000, "lon": 34.6333, "cap": 600.0, "init_stock": 520.0, "cons_rate": 6.0, "deadline": 120.0},
        {"name": "Canakkale", "lat": 40.1553, "lon": 26.4142, "cap": 350.0, "init_stock": 300.0, "cons_rate": 3.0, "deadline": 90.0},
        {"name": "Izmir", "lat": 38.4237, "lon": 27.1428, "cap": 480.0, "init_stock": 360.0, "cons_rate": 4.5, "deadline": 100.0},
        {"name": "Samsun", "lat": 41.2867, "lon": 36.3300, "cap": 390.0, "init_stock": 300.0, "cons_rate": 3.8, "deadline": 105.0},
    ],
}

DEFAULT_SHIP = {
    "empty_weight": 2000.0,
    "pump_rate": 50.0,
    "prep_time": 0.5,
    "charter_rate": 500.0,
    "fuel_cost": 0.02,
    "speed": 15.0,
}

MENU_ITEMS = ["Home", "Optimizer", "Plant Map"]


# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------

def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #f3f7fb 0%, #eef4f8 100%);
            color: #0f172a;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #172554 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        [data-testid="stSidebar"] * {
            color: #f8fafc;
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            color: #0f172a;
        }
        .hero {
            background: linear-gradient(135deg, #0f766e 0%, #2563eb 55%, #7c3aed 100%);
            padding: 1.4rem 1.5rem;
            border-radius: 24px;
            color: white;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
            margin-bottom: 1rem;
        }
        .hero h1 {
            color: white;
            margin: 0;
            font-size: 2rem;
            line-height: 1.15;
        }
        .hero p {
            margin: 0.45rem 0 0 0;
            opacity: 0.95;
            font-size: 1rem;
        }
        .quick-card {
            border-radius: 22px;
            padding: 1rem 1.1rem;
            color: white;
            min-height: 128px;
            border: 1px solid rgba(255,255,255,0.14);
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.10);
            margin-bottom: 0.75rem;
        }
        .quick-card h4 {
            margin: 0;
            font-size: 0.9rem;
            font-weight: 600;
            opacity: 0.92;
        }
        .quick-card .value {
            margin-top: 0.45rem;
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.1;
        }
        .quick-card .note {
            margin-top: 0.35rem;
            font-size: 0.9rem;
            opacity: 0.92;
        }
        .teal { background: linear-gradient(135deg, #0f766e, #14b8a6); }
        .blue { background: linear-gradient(135deg, #1d4ed8, #60a5fa); }
        .purple { background: linear-gradient(135deg, #6d28d9, #a78bfa); }
        .orange { background: linear-gradient(135deg, #ea580c, #fb923c); }
        .soft-panel {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid #dbe3ec;
            border-radius: 22px;
            padding: 1rem 1rem 0.85rem 1rem;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
            margin-bottom: 1rem;
        }
        .mini-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .help-box {
            background: rgba(255,255,255,0.96);
            border-left: 6px solid #14b8a6;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            color: #0f172a;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 14px;
            border: 0;
            min-height: 2.9rem;
            font-weight: 700;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.12);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
        }
        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.82);
            border-radius: 12px 12px 0 0;
            padding: 0.55rem 1rem;
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(148, 163, 184, 0.18);
            padding: 0.8rem;
            border-radius: 18px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
        }
        .nav-note {
            font-size: 0.85rem;
            color: #cbd5e1;
            line-height: 1.45;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dbe3ec;
            color: #0f172a;
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stMetricDelta"] {
            color: #0f172a !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.12);
            box-shadow: none;
        }
        [data-testid="stSidebar"] [data-testid="stMetricLabel"],
        [data-testid="stSidebar"] [data-testid="stMetricValue"],
        [data-testid="stSidebar"] [data-testid="stMetricDelta"] {
            color: #f8fafc !important;
        }
        div[data-baseweb="input"],
        div[data-baseweb="base-input"] {
            background: #ffffff !important;
            border-radius: 12px !important;
            border: 1px solid #cbd5e1 !important;
        }
        input, textarea {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }
        label[data-testid="stWidgetLabel"] p,
        .stSelectbox label p,
        .stNumberInput label p,
        .stToggle label p,
        .stRadio label p {
            color: #0f172a !important;
            font-weight: 600;
        }
        [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] .stRadio label p {
            color: #f8fafc !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stHorizontalBlock"] > div:has(> [data-testid="stVerticalBlockBorderWrapper"]) {
            background: rgba(255,255,255,0.92);
            border-radius: 18px;
        }
        .stDataFrame, .stTable {
            background: rgba(255,255,255,0.96);
            border-radius: 16px;
        }
        [data-baseweb="tab"] {
            color: #0f172a !important;
            font-weight: 600;
        }
        [aria-selected="true"][data-baseweb="tab"] {
            background: #ffffff !important;
            color: #0f172a !important;
            border-bottom: 3px solid #2563eb;
        }
        .stAlert {
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_custom_css()


# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


@st.cache_data(show_spinner=False)
def compute_distance_matrix(depot_lat: float, depot_lon: float, plant_rows: List[Dict]):
    n = len(plant_rows)
    dist = [[0.0] * (n + 2) for _ in range(n + 2)]
    points = [(depot_lat, depot_lon)] + [(p["lat"], p["lon"]) for p in plant_rows]
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                dist[i][j] = round(
                    haversine_nm(points[i][0], points[i][1], points[j][0], points[j][1]),
                    1,
                )
    return dist


def make_active_plant_rows() -> List[Dict]:
    rows = []
    for i, item in enumerate(st.session_state.fixed_plants):
        if item["enabled"]:
            rows.append(
                {
                    "id": i + 1,
                    "name": item["name"],
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"]),
                    "cap": float(item["cap"]),
                    "init_stock": float(item["init_stock"]),
                    "cons_rate": float(item["cons_rate"]),
                    "deadline": float(item["deadline"]),
                }
            )
    return rows


def make_plants(rows: List[Dict]) -> List[Plant]:
    return [
        Plant(
            name=row["name"],
            cap=row["cap"],
            init_stock=row["init_stock"],
            cons_rate=row["cons_rate"],
            deadline=row["deadline"],
        )
        for row in rows
    ]


def build_bundle(result: Dict) -> bytes:
    return json.dumps(
        {
            "status": result.get("status"),
            "voyage_time": result.get("voyage_time"),
            "total_cost": result.get("total_cost"),
            "route_labels": result.get("route_labels"),
            "deliveries": result.get("deliveries"),
            "arcs": result.get("arcs"),
        },
        indent=2,
    ).encode("utf-8")


def navigate(page_name: str) -> None:
    st.session_state.nav_page = page_name
    st.rerun()


def quick_card(title: str, value: str, note: str, tone: str = "blue") -> None:
    st.markdown(
        f"""
        <div class="quick-card {tone}">
            <h4>{title}</h4>
            <div class="value">{value}</div>
            <div class="note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_panel(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="help-box">
            <div class="mini-title">{title}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(value: bool) -> str:
    return "Active" if value else "Off"


# -----------------------------------------------------------------------------
# Maps
# -----------------------------------------------------------------------------

def render_plant_map(active_rows: List[Dict], depot: Dict, chart_key: str = "plant-map") -> None:
    fig = go.Figure()

    fig.add_trace(
        go.Scattermapbox(
            lat=[depot["lat"]],
            lon=[depot["lon"]],
            mode="markers+text",
            marker=dict(size=20, color="#1d4ed8"),
            text=["D"],
            textfont=dict(size=12, color="#ffffff"),
            textposition="middle center",
            name="Depot",
            customdata=[f"<b>{depot['name']}</b><br>Depot"],
            hovertemplate="%{customdata}<extra></extra>",
        )
    )

    if active_rows:
        hover_rows = []
        for row in active_rows:
            hover_rows.append(
                "<br>".join(
                    [
                        f"<b>{row['name']}</b>",
                        f"Plant #{row['id']}",
                        f"Capacity: {row['cap']:.0f} T",
                        f"Initial stock: {row['init_stock']:.0f} T",
                        f"Consumption: {row['cons_rate']:.1f} T/hr",
                        f"Deadline: {row['deadline']:.1f} hr",
                    ]
                )
            )

        fig.add_trace(
            go.Scattermapbox(
                lat=[row["lat"] for row in active_rows],
                lon=[row["lon"] for row in active_rows],
                mode="markers+text",
                marker=dict(size=21, color="#14b8a6"),
                text=[str(row["id"]) for row in active_rows],
                textfont=dict(size=12, color="#ffffff"),
                textposition="middle center",
                name="Plants",
                customdata=hover_rows,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


def render_solution_map(result: Dict, active_rows: List[Dict], depot: Dict, chart_key: str = "solution-map") -> None:
    coord_map = {"Depot": (depot["lat"], depot["lon"]), depot["name"]: (depot["lat"], depot["lon"])}
    for row in active_rows:
        coord_map[row["name"]] = (row["lat"], row["lon"])

    visit_order: Dict[str, int] = {}
    order = 1
    for label in result["route_labels"]:
        if label in {"Depot", "End of service", "Depot (return)"}:
            continue
        if label in coord_map and label not in visit_order:
            visit_order[label] = order
            order += 1

    fig = go.Figure()
    fig.add_trace(
        go.Scattermapbox(
            lat=[depot["lat"]],
            lon=[depot["lon"]],
            mode="markers+text",
            marker=dict(size=20, color="#1d4ed8"),
            text=["D"],
            textfont=dict(size=12, color="#ffffff"),
            textposition="middle center",
            name="Depot",
            customdata=[f"<b>{depot['name']}</b><br>Starting depot"],
            hovertemplate="%{customdata}<extra></extra>",
        )
    )

    visited_lat, visited_lon, visited_text, visited_hover = [], [], [], []
    idle_lat, idle_lon, idle_text, idle_hover = [], [], [], []

    for row in active_rows:
        delivery = next((d for d in result["deliveries"] if d["Plant"] == row["name"]), None)
        hover_lines = [f"<b>{row['name']}</b>"]
        if row["name"] in visit_order:
            hover_lines.append(f"Visit order: {visit_order[row['name']]}")
        else:
            hover_lines.append("Not visited in this solution")
        if delivery:
            late = delivery.get("Lateness (hr)", 0)
            hover_lines.extend(
                [
                    f"Arrival: {delivery['Arrival (hr)']} hr",
                    f"Deadline: {delivery['Eff. Deadline (hr)']} hr",
                    f"Delivered: {delivery['Delivered (T)']} T",
                    f"Lateness: {late:.3f} hr",
                ]
            )
        hover_text = "<br>".join(hover_lines)

        if row["name"] in visit_order:
            visited_lat.append(row["lat"])
            visited_lon.append(row["lon"])
            visited_text.append(str(visit_order[row["name"]]))
            visited_hover.append(hover_text)
        else:
            idle_lat.append(row["lat"])
            idle_lon.append(row["lon"])
            idle_text.append(str(row["id"]))
            idle_hover.append(hover_text)

    if idle_lat:
        fig.add_trace(
            go.Scattermapbox(
                lat=idle_lat,
                lon=idle_lon,
                mode="markers+text",
                marker=dict(size=18, color="#f59e0b"),
                text=idle_text,
                textfont=dict(size=11, color="#ffffff"),
                textposition="middle center",
                name="Unvisited",
                customdata=idle_hover,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    if visited_lat:
        fig.add_trace(
            go.Scattermapbox(
                lat=visited_lat,
                lon=visited_lon,
                mode="markers+text",
                marker=dict(size=22, color="#ef4444"),
                text=visited_text,
                textfont=dict(size=12, color="#ffffff"),
                textposition="middle center",
                name="Visit order",
                customdata=visited_hover,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


# -----------------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------------

def render_results(multi: Dict, active_rows: List[Dict], depot: Dict) -> None:
    if isinstance(multi, str):
        st.error(multi)
        return

    if multi.get("kind") == "validation_error":
        st.error("Input validation failed.")
        for issue in multi["diagnostics"]["issues"]:
            st.write(f"- {issue}")
        return

    if multi.get("kind") == "infeasible":
        st.error(multi["message"])
        checks = pd.DataFrame(multi["diagnostics"].get("plant_checks", []))
        if not checks.empty:
            st.dataframe(checks, use_container_width=True, hide_index=True)
        return

    solutions = multi.get("solutions", [])
    st.caption(f"Found {multi.get('n_found', len(solutions))} solution(s) | Solve time: {multi['elapsed']} s")

    for warning in multi.get("diagnostics", {}).get("warnings", []):
        st.warning(warning)

    if len(solutions) == 1:
        solution = solutions[0]
        st.markdown(f"### Solution #1 — {solution['status']}")
        render_one_solution(solution, active_rows, depot, rank=1)
    else:
        tabs = st.tabs([f"Solution #{sol['solution_rank']} — {sol['status']}" for sol in solutions])
        for tab, solution in zip(tabs, solutions):
            with tab:
                render_one_solution(solution, active_rows, depot, rank=solution["solution_rank"])


def render_one_solution(result: Dict, active_rows: List[Dict], depot: Dict, rank: int = 1) -> None:
    on_time = sum(1 for delivery in result["deliveries"] if delivery["On Time"])
    total_plants = len(result["deliveries"])
    late_count = total_plants - on_time

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total cost", f"${result['total_cost']:,.0f}")
    c2.metric("Voyage time", f"{result['voyage_time']:.2f} hr")
    c3.metric("On-time deliveries", f"{on_time} / {total_plants}")
    if late_count > 0:
        c4.metric(
            "Lateness penalty",
            f"${result['lateness_penalty']:,.0f}",
            delta=f"{late_count} plant(s) late",
            delta_color="inverse",
        )
    else:
        c4.metric("Lateness penalty", "$0", delta="All on time", delta_color="normal")

    st.markdown("**Route:** " + " → ".join(result["route_labels"]))

    tab1, tab2, tab3, tab4 = st.tabs(["Map", "Deliveries", "Costs", "Technical details"])

    with tab1:
        render_solution_map(result, active_rows, depot, chart_key=f"solution-map-{rank}")

    with tab2:
        df = pd.DataFrame(result["deliveries"])
        if not df.empty:
            bar_df = df[["Plant", "Delivered (T)"]].copy()
            bar_df["Delivered (T)"] = pd.to_numeric(bar_df["Delivered (T)"], errors="coerce").fillna(0)

            fig = go.Figure(
                data=[
                    go.Bar(
                        x=bar_df["Plant"],
                        y=bar_df["Delivered (T)"],
                        text=bar_df["Delivered (T)"],
                        textposition="outside",
                    )
                ]
            )
            fig.update_layout(
                title="Delivered quantity by plant",
                xaxis_title="Plant",
                yaxis_title="Delivered (T)",
            )
            st.plotly_chart(fig, use_container_width=True, key=f"deliveries-bar-{rank}")

        def highlight_late(row: pd.Series):
            if not row.get("On Time", True):
                return ["background-color: #fff1f2"] * len(row)
            return [""] * len(row)

        st.dataframe(df.style.apply(highlight_late, axis=1), use_container_width=True, hide_index=True)
        st.download_button(
            "Download deliveries CSV",
            df.to_csv(index=False).encode("utf-8"),
            f"deliveries_sol{rank}.csv",
            "text/csv",
            key=f"download-deliveries-{rank}",
        )

    with tab3:
        cost_df = pd.DataFrame(
            [
                {"Component": "Charter cost", "Value ($)": round(result["charter"], 2)},
                {"Component": "Empty-ship fuel cost", "Value ($)": round(result["empty_fuel"], 2)},
                {"Component": "Cargo fuel cost", "Value ($)": round(result["cargo_fuel"], 2)},
                {"Component": "Lateness penalty", "Value ($)": round(result["lateness_penalty"], 2)},
            ]
        )

        fig = go.Figure(
            data=[
                go.Bar(
                    x=cost_df["Component"],
                    y=cost_df["Value ($)"],
                    text=cost_df["Value ($)"].round(2),
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(title="Cost breakdown", xaxis_title="Component", yaxis_title="Cost ($)")
        st.plotly_chart(fig, use_container_width=True, key=f"cost-bar-{rank}")

        total_row = pd.DataFrame([{"Component": "TOTAL", "Value ($)": round(result["total_cost"], 2)}])
        st.dataframe(pd.concat([cost_df, total_row], ignore_index=True), use_container_width=True, hide_index=True)
        st.download_button(
            "Download result JSON",
            build_bundle(result),
            f"mirp_result_sol{rank}.json",
            "application/json",
            key=f"download-json-{rank}",
        )

    with tab4:
        st.markdown("#### Active arcs")
        st.dataframe(pd.DataFrame(result["arcs"]), use_container_width=True, hide_index=True)
        pre = result.get("pre", {})
        if pre:
            st.markdown("#### Model coefficients")
            st.write(
                {
                    "worst_case_cargo_Q": round(pre.get("Q", 0.0), 3),
                    "penalty_coefficient": pre.get("penalty"),
                    "alpha": {i: round(v, 3) for i, v in pre.get("alpha", {}).items()},
                    "beta": {i: round(v, 4) for i, v in pre.get("beta", {}).items()},
                    "eff_l": {i: round(v, 2) for i, v in pre.get("eff_l", {}).items()},
                    "L_i": pre.get("L", {}),
                    "terminal_label": pre.get("terminal_label"),
                }
            )
        st.caption(
            f"OR-Tools SCIP | Variables: {result['n_vars']} | Constraints: {result['n_cons']} | Solve time: {result['elapsed']} s"
        )


# -----------------------------------------------------------------------------
# Page sections
# -----------------------------------------------------------------------------

def render_sidebar() -> None:
    st.sidebar.markdown("## ⚓ Maritime DSS")
    st.sidebar.markdown('<div class="nav-note">Simple navigation for setup, optimization, and plant monitoring.</div>', unsafe_allow_html=True)
    current_index = MENU_ITEMS.index(st.session_state.nav_page)
    selected = st.sidebar.radio("Main menu", MENU_ITEMS, index=current_index)
    if selected != st.session_state.nav_page:
        st.session_state.nav_page = selected
        st.rerun()

    active_rows = make_active_plant_rows()
    st.sidebar.divider()
    st.sidebar.metric("Active plants", len(active_rows))
    st.sidebar.metric("Saved results", 0 if st.session_state.last_result is None else 1)
    st.sidebar.metric("Default speed", f"{DEFAULT_SHIP['speed']:.0f} NM/hr")
    st.sidebar.divider()
    st.sidebar.caption("Use Home for quick access, Optimizer for setup and results, and Plant Map for the network overview.")


def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home() -> None:
    render_header()
    active_rows = make_active_plant_rows()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        quick_card("Plants in network", str(len(FIXED_SCENARIO["plants"])), "Monitor all plant locations", "teal")
    with k2:
        quick_card("Currently active", str(len(active_rows)), "Used in optimization", "blue")
    with k3:
        quick_card("Route modes", "2", "Open route or closed route", "purple")
    with k4:
        quick_card("Main views", "3", "Home, Optimizer, Plant Map", "orange")

    left, right = st.columns([1.1, 0.9])

    with left:
        info_panel(
            "How to use",
            "Start from the optimizer to choose active plants and vessel inputs. Then run the model and check the map, deliveries, and cost breakdown.",
        )

        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("Open optimizer", type="primary", use_container_width=True):
                navigate("Optimizer")
        with button_col2:
            if st.button("View plant map", use_container_width=True):
                navigate("Plant Map")

        st.markdown("### Quick scenario overview")
        summary_df = pd.DataFrame(
            [
                {
                    "Plant": row["name"],
                    "Status": status_badge(row["enabled"]),
                    "Capacity (T)": row["cap"],
                    "Initial stock (T)": row["init_stock"],
                    "Deadline (hr)": row["deadline"],
                }
                for row in st.session_state.fixed_plants
            ]
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Active plant map")
        render_plant_map(active_rows, FIXED_SCENARIO["depot"], chart_key="home-plant-map")


def render_plant_map_page() -> None:
    render_header()
    depot = FIXED_SCENARIO["depot"]
    active_rows = make_active_plant_rows()

    left, right = st.columns([0.95, 1.05])
    with left:
        info_panel(
            "Map meaning",
            "Blue marker = depot. Green numbered markers = active plants. The number inside each marker is the plant number used for easier visual reference.",
        )
        st.markdown("### Plant summary")
        table_df = pd.DataFrame(active_rows if active_rows else [])
        if table_df.empty:
            st.warning("No active plants selected. Enable plants from the Optimizer page.")
        else:
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            st.metric("Average deadline", f"{table_df['deadline'].mean():.1f} hr")
            st.metric("Average consumption", f"{table_df['cons_rate'].mean():.2f} T/hr")

    with right:
        st.markdown("### Network map")
        render_plant_map(active_rows, depot, chart_key="network-plant-map")


def render_optimizer() -> None:
    render_header()
    depot = FIXED_SCENARIO["depot"]

    setup_tab, results_tab = st.tabs(["Scenario setup", "Results"])

    with setup_tab:
        top_left, top_right = st.columns([1.25, 0.95])

        with top_left:
            st.markdown("### Select active plants")
            info_panel(
                "Plant setup",
                "Turn plants on or off, then adjust capacity, stock, consumption, and deadline values. Keeping only relevant plants makes the scenario easier to read.",
            )

            columns = st.columns(2)
            for idx, plant in enumerate(st.session_state.fixed_plants):
                with columns[idx % 2]:
                    with st.container(border=True):
                        toggle_col, title_col = st.columns([0.8, 1.2])
                        with toggle_col:
                            plant["enabled"] = st.toggle(
                                f"Use {plant['name']}",
                                value=plant["enabled"],
                                key=f"enabled_{idx}",
                            )
                        with title_col:
                            st.markdown(f"**{plant['name']}**")
                            st.caption(f"Lat {plant['lat']:.4f} | Lon {plant['lon']:.4f}")

                        c1, c2 = st.columns(2)
                        plant["cap"] = c1.number_input(
                            f"Capacity - {plant['name']}",
                            min_value=0.0,
                            value=float(plant["cap"]),
                            step=10.0,
                            key=f"cap_{idx}",
                        )
                        plant["init_stock"] = c2.number_input(
                            f"Initial stock - {plant['name']}",
                            min_value=0.0,
                            value=float(plant["init_stock"]),
                            step=10.0,
                            key=f"init_{idx}",
                        )
                        c3, c4 = st.columns(2)
                        plant["cons_rate"] = c3.number_input(
                            f"Consumption - {plant['name']}",
                            min_value=0.01,
                            value=float(plant["cons_rate"]),
                            step=0.1,
                            key=f"cons_{idx}",
                        )
                        plant["deadline"] = c4.number_input(
                            f"Deadline - {plant['name']}",
                            min_value=0.1,
                            value=float(plant.get("deadline") or plant["init_stock"] / plant["cons_rate"]),
                            step=1.0,
                            key=f"ddl_{idx}",
                        )

        with top_right:
            st.markdown("### Vessel and solver settings")
            with st.container(border=True):
                c1, c2 = st.columns(2)
                empty_weight = c1.number_input("Empty weight (T)", min_value=0.0, value=DEFAULT_SHIP["empty_weight"], step=100.0)
                pump_rate = c2.number_input("Pump rate (T/hr)", min_value=0.1, value=DEFAULT_SHIP["pump_rate"], step=5.0)
                prep_time = c1.number_input("Preparation time (hr)", min_value=0.0, value=DEFAULT_SHIP["prep_time"], step=0.1)
                charter_rate = c2.number_input("Charter rate ($/hr)", min_value=0.0, value=DEFAULT_SHIP["charter_rate"], step=50.0)
                fuel_cost = c1.number_input("Fuel cost ($/Ton-NM)", min_value=0.0, value=DEFAULT_SHIP["fuel_cost"], step=0.01, format="%.4f")
                speed = c2.number_input("Speed (NM/hr)", min_value=0.1, value=DEFAULT_SHIP["speed"], step=1.0)

            with st.container(border=True):
                o1, o2, o3 = st.columns(3)
                return_to_depot = o1.toggle("Closed route", value=False, help="If enabled, the vessel returns to depot after the last delivery.")
                top_n = o2.number_input("Top N solutions", min_value=1, max_value=10, value=1, step=1)
                penalty = o3.number_input(
                    "Penalty coefficient (P)",
                    min_value=0.0,
                    value=1_000_000.0,
                    step=100_000.0,
                    format="%.0f",
                    help="Higher penalty makes the model avoid lateness more strongly.",
                )
                st.caption("Soft-deadline model: lateness is allowed but penalized.")

            active_rows = make_active_plant_rows()
            route_mode = "Closed route" if return_to_depot else "Open route"
            ship = Ship(
                empty_weight=empty_weight,
                pump_rate=pump_rate,
                prep_time=prep_time,
                charter_rate=charter_rate,
                fuel_cost=fuel_cost,
                speed=speed,
            )

            show_summary = st.container(border=True)
            with show_summary:
                st.markdown("#### Quick summary")
                a, b, c, d = st.columns(4)
                a.metric("Active plants", len(active_rows))
                b.metric("Route type", route_mode)
                c.metric("Vessel speed", f"{ship.speed:.1f} NM/hr")
                d.metric("Pump rate", f"{ship.pump_rate:.1f} T/hr")

            if active_rows:
                plants = make_plants(active_rows)
                dist = compute_distance_matrix(depot["lat"], depot["lon"], active_rows)
                diagnostics = quick_diagnostics(plants, ship, dist, return_to_depot=return_to_depot)

                for warning in diagnostics.get("warnings", []):
                    st.warning(warning)
                for issue in diagnostics.get("issues", []):
                    st.error(issue)

                if st.button("Run optimization", type="primary", use_container_width=True):
                    with st.spinner("Solving..."):
                        result = run_solver(
                            plants,
                            ship,
                            dist,
                            penalty=penalty,
                            return_to_depot=return_to_depot,
                            top_n=int(top_n),
                        )
                    st.session_state.last_result = result
                    st.session_state.last_inputs = {"active_rows": active_rows, "depot": depot}
                    st.success("Optimization complete. Open the Results tab.")
            else:
                st.error("Select at least one plant to create a scenario.")

        active_rows = make_active_plant_rows()
        if active_rows:
            st.markdown("### Active plant table")
            st.dataframe(pd.DataFrame(active_rows), use_container_width=True, hide_index=True)

    with results_tab:
        st.markdown("### Optimization results")
        if st.session_state.last_result is None:
            info_panel(
                "No result yet",
                "Run the model from the Scenario setup tab to view optimization results here.",
            )
        else:
            render_results(
                st.session_state.last_result,
                st.session_state.last_inputs["active_rows"],
                st.session_state.last_inputs["depot"],
            )


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------

if "fixed_plants" not in st.session_state:
    st.session_state.fixed_plants = [dict(item, enabled=True) for item in FIXED_SCENARIO["plants"]]
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_inputs" not in st.session_state:
    st.session_state.last_inputs = None
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Home"


# -----------------------------------------------------------------------------
# App shell
# -----------------------------------------------------------------------------

render_sidebar()

if st.session_state.nav_page == "Home":
    render_home()
elif st.session_state.nav_page == "Optimizer":
    render_optimizer()
else:
    render_plant_map_page()
