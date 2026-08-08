"""
Concept Chain - a causal concept-mapping study tool.

Built for subjects like Indian Economy where understanding *why* something
formed, what problem it solved, and what it led to next matters more than
memorizing isolated facts. Every concept you add must state the problem it
solved and what caused it - the app then builds a timeline/causal graph and
a quiz mode from that structure.

Run: streamlit run app.py
"""
import json
import random
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Concept Chain", page_icon="🧠", layout="wide")

DATA_FILE = Path("concept_data.json")

CATEGORIES = ["Monetary", "Fiscal", "External", "Social", "Political", "Other"]
CATEGORY_COLORS = {
    "Monetary": "#1a56db",
    "Fiscal": "#d6336c",
    "External": "#0f9d58",
    "Social": "#f59e0b",
    "Political": "#7c3aed",
    "Other": "#6b7280",
}

STARTER_PACK = [
    dict(name="Reserve Bank of India (RBI)", abbr="RBI", category="Monetary", year=1935,
         problem="A new colonial economy had no central authority to issue currency or "
                 "stabilize the monetary system - RBI was formed to control money supply "
                 "and manage the currency.",
         caused_by=[], notes=""),
    dict(name="Planning Commission / Five Year Plans", abbr="FYP", category="Fiscal", year=1951,
         problem="Independent India had very low private capital. The state had to "
                 "directly plan and direct investment into infrastructure and industry "
                 "because private markets alone couldn't mobilize enough capital.",
         caused_by=[], notes=""),
    dict(name="Bank Nationalization", abbr="", category="Monetary", year=1969,
         problem="Private banks were lending mostly to large urban businesses. Credit "
                 "wasn't reaching agriculture or rural priority sectors, so the "
                 "government took control of major banks to redirect lending.",
         caused_by=["Reserve Bank of India (RBI)"], notes=""),
    dict(name="License Raj / Industrial Licensing", abbr="", category="Political", year=1951,
         problem="To make sure planned investment (from the Five Year Plans) went where "
                 "the state intended, private industry needed government permission to "
                 "expand or start production - this became the License Raj.",
         caused_by=["Planning Commission / Five Year Plans"], notes=""),
    dict(name="Balance of Payments Crisis", abbr="BoP Crisis", category="External", year=1991,
         problem="Decades of import-heavy, licensing-restricted growth plus an oil price "
                 "shock left India with barely enough foreign reserves to cover 2 weeks "
                 "of imports - a full-blown external payments crisis.",
         caused_by=["License Raj / Industrial Licensing"], notes=""),
    dict(name="LPG Reforms (Liberalization, Privatization, Globalization)", abbr="LPG",
         category="Political", year=1991,
         problem="With foreign reserves nearly exhausted, India had no choice but to "
                 "dismantle licensing, open up to foreign investment, and devalue the "
                 "rupee in exchange for an IMF bailout.",
         caused_by=["Balance of Payments Crisis"], notes=""),
    dict(name="Securities and Exchange Board of India (SEBI)", abbr="SEBI", category="Monetary",
         year=1992,
         problem="As markets opened up post-1991, stock markets needed a real regulator "
                 "to protect investors and prevent manipulation - SEBI was given "
                 "statutory power after the Harshad Mehta scam exposed the gap.",
         caused_by=["LPG Reforms (Liberalization, Privatization, Globalization)"], notes=""),
    dict(name="Foreign Exchange Management Act", abbr="FEMA", category="External", year=1999,
         problem="The older FERA law treated all foreign exchange as suspicious and "
                 "criminal. A liberalizing economy needed a facilitative law instead of "
                 "a restrictive one - FEMA replaced FERA.",
         caused_by=["LPG Reforms (Liberalization, Privatization, Globalization)"], notes=""),
    dict(name="Fiscal Responsibility and Budget Management Act", abbr="FRBM", category="Fiscal",
         year=2003,
         problem="Government deficits kept spiraling with no legal ceiling. FRBM forced "
                 "the government to set and follow numerical deficit targets.",
         caused_by=["Planning Commission / Five Year Plans"], notes=""),
    dict(name="NITI Aayog", abbr="NITI", category="Political", year=2015,
         problem="Top-down five-year command planning didn't fit a liberalized, "
                 "market-driven economy anymore - NITI Aayog replaced the Planning "
                 "Commission as a policy think tank instead of a resource allocator.",
         caused_by=["Planning Commission / Five Year Plans",
                     "LPG Reforms (Liberalization, Privatization, Globalization)"], notes=""),
    dict(name="Monetary Policy Committee / Inflation Targeting", abbr="MPC", category="Monetary",
         year=2016,
         problem="RBI's interest rate decisions used to be discretionary and opaque. A "
                 "formal committee with an explicit inflation target (4% +/-2%) was "
                 "created to make monetary policy predictable and rules-based.",
         caused_by=["Reserve Bank of India (RBI)"], notes=""),
    dict(name="Goods and Services Tax", abbr="GST", category="Fiscal", year=2017,
         problem="Dozens of overlapping state and central taxes (VAT, excise, service "
                 "tax) caused cascading 'tax on tax' effects. GST unified them into one "
                 "nationwide tax to fix that.",
         caused_by=["Fiscal Responsibility and Budget Management Act"], notes=""),
    dict(name="Pradhan Mantri Jan Dhan Yojana", abbr="PMJDY", category="Social", year=2014,
         problem="A large share of the population had no bank account, so government "
                 "subsidies leaked through middlemen. PMJDY gave nearly every household "
                 "a zero-balance bank account to receive direct transfers.",
         caused_by=["Bank Nationalization"], notes=""),
    dict(name="Unified Payments Interface", abbr="UPI", category="Monetary", year=2016,
         problem="Once most people had bank accounts (via PMJDY) but digital payments "
                 "were fragmented across apps and banks, UPI created one common, "
                 "instant, interoperable payment rail.",
         caused_by=["Pradhan Mantri Jan Dhan Yojana"], notes=""),
    dict(name="Insolvency and Bankruptcy Code", abbr="IBC", category="Fiscal", year=2016,
         problem="Banks (nationalized decades earlier) had accumulated huge bad loans "
                 "with no fast legal way to recover money from failed companies - IBC "
                 "created a time-bound resolution process.",
         caused_by=["Bank Nationalization"], notes=""),
]

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "node"


def load_nodes():
    if "nodes" not in st.session_state:
        if DATA_FILE.exists():
            try:
                st.session_state.nodes = json.loads(DATA_FILE.read_text())
            except Exception:
                st.session_state.nodes = []
        else:
            st.session_state.nodes = []
    return st.session_state.nodes


def save_nodes():
    try:
        DATA_FILE.write_text(json.dumps(st.session_state.nodes, indent=2))
    except Exception:
        pass  # Streamlit Cloud's filesystem may be read-only/ephemeral; download/upload covers that


def next_id(name: str) -> str:
    base = slugify(name)
    existing_ids = {n["id"] for n in st.session_state.nodes}
    candidate = base
    i = 2
    while candidate in existing_ids:
        candidate = f"{base}-{i}"
        i += 1
    return candidate


def id_by_name(name: str):
    for n in st.session_state.nodes:
        if n["name"] == name:
            return n["id"]
    return None


def name_by_id(node_id: str):
    for n in st.session_state.nodes:
        if n["id"] == node_id:
            return n["name"]
    return node_id


def children_of(node_id: str):
    """Nodes that list node_id as one of their causes."""
    return [n for n in st.session_state.nodes if node_id in n.get("caused_by", [])]


def parents_of(node):
    return [name_by_id(pid) for pid in node.get("caused_by", [])]


# ---------------------------------------------------------------------------
# Graph layout (timeline x category swimlanes)
# ---------------------------------------------------------------------------
def compute_positions(nodes):
    """x = chronological order (year if present, else insertion order),
    y = category lane, with small jitter so same-year/category nodes don't overlap."""
    positions = {}
    cat_index = {c: i for i, c in enumerate(CATEGORIES)}

    # Assign an x value: real year if given, else spread unplaced nodes after the max year
    years = [n["year"] for n in nodes if n.get("year")]
    fallback_x = (max(years) + 1) if years else 0

    lane_occupants = {}  # (x_rounded, category) -> count, for jitter
    for n in nodes:
        x = n["year"] if n.get("year") else fallback_x
        if not n.get("year"):
            fallback_x += 1
        cat = n.get("category", "Other")
        y_base = cat_index.get(cat, len(CATEGORIES))
        key = (x, cat)
        offset = lane_occupants.get(key, 0)
        lane_occupants[key] = offset + 1
        y = y_base + offset * 0.32
        positions[n["id"]] = (x, y)
    return positions


def build_figure(nodes):
    if not nodes:
        return None
    positions = compute_positions(nodes)

    fig = go.Figure()

    # Edges (causal links) drawn first so they sit behind nodes
    for n in nodes:
        x1, y1 = positions[n["id"]]
        for parent_id in n.get("caused_by", []):
            if parent_id not in positions:
                continue
            x0, y0 = positions[parent_id]
            fig.add_annotation(
                x=x1, y=y1, ax=x0, ay=y0,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=1.4,
                arrowcolor="#9ca3af", opacity=0.75,
            )

    # Nodes, one trace per category so the legend doubles as a color key
    for cat in CATEGORIES:
        cat_nodes = [n for n in nodes if n.get("category", "Other") == cat]
        if not cat_nodes:
            continue
        xs = [positions[n["id"]][0] for n in cat_nodes]
        ys = [positions[n["id"]][1] for n in cat_nodes]
        labels = [n["name"] + (f" ({n['abbr']})" if n.get("abbr") else "") for n in cat_nodes]
        hover = [
            f"<b>{n['name']}</b><br>{n.get('year', 'no year')} - {cat}<br><br>"
            f"{n['problem'][:180]}{'...' if len(n['problem']) > 180 else ''}"
            for n in cat_nodes
        ]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text", name=cat,
            text=labels, textposition="top center", textfont=dict(size=10),
            marker=dict(size=14, color=CATEGORY_COLORS[cat], line=dict(width=1, color="white")),
            hovertext=hover, hoverinfo="text",
        ))

    fig.update_layout(
        height=560,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Year (chronological flow →)",
        yaxis=dict(showticklabels=False, title=None),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="#fafafa",
    )
    return fig


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
nodes = load_nodes()

st.title("🧠 Concept Chain")
st.caption(
    "Map out *why* things formed, not just what they're called. Build the causal "
    "chain for any subject - economics, history, systems - and quiz yourself on it."
)

if not nodes:
    st.info(
        "No concepts yet. Load the Indian Economy starter pack below, or add your "
        "first concept in the sidebar."
    )
    if st.button("Load Indian Economy starter pack"):
        st.session_state.nodes = [
            {**item, "id": next_id(item["name"])} for item in STARTER_PACK
        ]
        # second pass to convert caused_by names -> ids now that all ids exist
        for n in st.session_state.nodes:
            n["caused_by"] = [id_by_name(name) for name in n["caused_by"] if id_by_name(name)]
        save_nodes()
        st.rerun()

# ---------------------------------------------------------------------------
# Sidebar - add a concept
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("➕ Add a concept")
    with st.form("add_concept", clear_on_submit=True):
        name = st.text_input("Name *", placeholder="e.g. Goods and Services Tax")
        abbr = st.text_input("Abbreviation", placeholder="e.g. GST")
        category = st.selectbox("Category", CATEGORIES)
        year = st.number_input("Year (leave 0 if unknown/ongoing)", min_value=0, max_value=2100,
                                value=0, step=1)
        problem = st.text_area(
            "What problem did it solve? (the 'why') *",
            placeholder="Why did this get created - what was broken before it?",
            height=100,
        )
        existing_names = [n["name"] for n in st.session_state.get("nodes", [])]
        caused_by_names = st.multiselect("Caused by / formed because of", existing_names)
        notes = st.text_area("Extra notes (optional)", height=60)
        submitted = st.form_submit_button("Add concept", type="primary")

        if submitted:
            if not name.strip() or not problem.strip():
                st.error("Name and 'what problem did it solve' are required.")
            else:
                new_node = {
                    "id": next_id(name),
                    "name": name.strip(),
                    "abbr": abbr.strip(),
                    "category": category,
                    "year": int(year) if year else None,
                    "problem": problem.strip(),
                    "caused_by": [id_by_name(n) for n in caused_by_names if id_by_name(n)],
                    "notes": notes.strip(),
                }
                st.session_state.nodes.append(new_node)
                save_nodes()
                st.success(f"Added '{name}'.")
                st.rerun()

    st.divider()
    st.subheader("Data")
    if st.session_state.get("nodes"):
        st.download_button(
            "⬇️ Download data (JSON)",
            data=json.dumps(st.session_state.nodes, indent=2),
            file_name="concept_data.json",
            mime="application/json",
            use_container_width=True,
        )
    uploaded = st.file_uploader("⬆️ Load a saved JSON file", type=["json"])
    if uploaded is not None:
        try:
            loaded = json.loads(uploaded.getvalue())
            st.session_state.nodes = loaded
            save_nodes()
            st.success(f"Loaded {len(loaded)} concepts.")
            st.rerun()
        except Exception as e:
            st.error(f"Couldn't read that file: {e}")

    if st.session_state.get("nodes") and st.button("🗑️ Clear all (start a new subject)"):
        st.session_state.nodes = []
        save_nodes()
        st.rerun()

    st.caption(
        "💡 Streamlit Cloud's storage can reset on redeploy. Download your JSON "
        "regularly and keep it in your GitHub repo so you never lose progress."
    )

if not nodes:
    st.stop()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_graph, tab_explore, tab_quiz, tab_glossary, tab_data = st.tabs(
    ["🗺️ Causal Map", "🔍 Explore a concept", "🎯 Quiz me", "📖 Glossary", "🛠️ Manage data"]
)

with tab_graph:
    st.caption(
        "Each lane is a category, positioned left-to-right by year. Arrows point "
        "from cause → effect, so you can trace the whole chain visually."
    )
    fig = build_figure(nodes)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

with tab_explore:
    names_sorted = sorted([n["name"] for n in nodes])
    picked = st.selectbox("Pick a concept", names_sorted)
    node = next(n for n in nodes if n["name"] == picked)

    color = CATEGORY_COLORS.get(node.get("category", "Other"), "#6b7280")
    st.markdown(
        f"### {node['name']}" + (f" ({node['abbr']})" if node.get("abbr") else "")
    )
    st.markdown(
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:10px;font-size:0.85em;'>{node.get('category', 'Other')}</span> "
        f"&nbsp; {node.get('year') or 'no fixed year'}",
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(f"**Why it formed:** {node['problem']}")

    parents = parents_of(node)
    if parents:
        st.markdown(f"**Formed because of:** {', '.join(parents)}")
    else:
        st.markdown("**Formed because of:** *(root cause - nothing upstream recorded)*")

    kids = children_of(node["id"])
    if kids:
        st.markdown(f"**Led to:** {', '.join(k['name'] for k in kids)}")
    else:
        st.markdown("**Led to:** *(nothing downstream recorded yet)*")

    if node.get("notes"):
        st.markdown(f"**Notes:** {node['notes']}")

with tab_quiz:
    st.caption("You'll see a concept - try to recall *why* it formed before revealing the answer.")
    if "quiz_node_id" not in st.session_state or st.button("🔀 New question"):
        st.session_state.quiz_node_id = random.choice(nodes)["id"]

    qnode = next((n for n in nodes if n["id"] == st.session_state.quiz_node_id), nodes[0])
    color = CATEGORY_COLORS.get(qnode.get("category", "Other"), "#6b7280")
    st.markdown(
        f"<div style='padding:20px;border-radius:10px;border:2px solid {color};'>"
        f"<h3 style='margin:0;'>{qnode['name']}"
        f"{' (' + qnode['abbr'] + ')' if qnode.get('abbr') else ''}</h3>"
        f"<p style='color:#666;'>{qnode.get('year') or 'no fixed year'} · {qnode.get('category')}</p>"
        f"<p><b>Why did this form? What problem did it solve?</b></p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("Reveal answer"):
        st.info(qnode["problem"])
        parents = parents_of(qnode)
        if parents:
            st.caption(f"Formed because of: {', '.join(parents)}")

with tab_glossary:
    abbr_rows = [
        {"Abbreviation": n["abbr"], "Full name": n["name"], "Category": n.get("category", ""),
         "Why it exists": n["problem"]}
        for n in nodes if n.get("abbr")
    ]
    if abbr_rows:
        df = pd.DataFrame(abbr_rows).sort_values(["Category", "Abbreviation"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No abbreviations added yet.")

with tab_data:
    st.caption("Edit or delete concepts directly. Changes save automatically.")
    df = pd.DataFrame([
        {
            "name": n["name"], "abbr": n.get("abbr", ""), "category": n.get("category", ""),
            "year": n.get("year"), "problem": n["problem"],
            "caused_by": ", ".join(parents_of(n)), "id": n["id"],
        }
        for n in nodes
    ])
    st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)

    st.subheader("Delete a concept")
    del_name = st.selectbox("Choose a concept to delete", sorted(n["name"] for n in nodes),
                             key="del_select")
    if st.button("Delete", type="secondary"):
        del_id = id_by_name(del_name)
        st.session_state.nodes = [n for n in st.session_state.nodes if n["id"] != del_id]
        # also strip references to the deleted node from any children
        for n in st.session_state.nodes:
            n["caused_by"] = [c for c in n.get("caused_by", []) if c != del_id]
        save_nodes()
        st.success(f"Deleted '{del_name}'.")
        st.rerun()
