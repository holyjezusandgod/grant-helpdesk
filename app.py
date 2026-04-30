import os
import datetime
import streamlit as st
import bq_client
import config

st.set_page_config(page_title=config.APP_NAME, layout="wide", page_icon="🎯")

# ── Brand palette ──────────────────────────────────────────────────────────────
INDIGO  = "#4a52a3"
YELLOW  = "#f5c520"
GREEN   = "#2e9b2e"
BLUE    = "#2d6ee0"
RED     = "#e03c3c"
BG      = "#e8eef6"
CARD_BG = "#ffffff"
ROW_BG  = "#f7f9fc"

st.markdown(f"""
<style>
/* ── Global font ── */
html, body, .stApp, .stApp * {{
    font-family: "Inter", "Helvetica Neue", Arial, sans-serif !important;
    font-size: 14px;
}}

/* ── Global background ── */
.stApp {{
    background-color: {BG} !important;
}}
section[data-testid="stMain"] > div {{
    background-color: {BG} !important;
}}
.main .block-container {{
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
}}

/* ── Sidebar (filter panel) ── */
[data-testid="stSidebar"] {{
    background-color: {CARD_BG} !important;
    border-right: 1px solid #e8eef6 !important;
}}
[data-testid="stSidebar"] * {{
    color: #111827 !important;
}}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stPills label {{
    color: #6b7280 !important;
    font-size: 0.68rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 500;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: #111827 !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: #e8eef6 !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    color: #6b7280 !important;
}}
/* sidebar input field backgrounds */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div {{
    background-color: #f5f7fb !important;
    border-radius: 12px !important;
    border: none !important;
}}

/* ── Tabs ── */
button[data-baseweb="tab"] {{
    font-weight: 500 !important;
    color: #6b7280 !important;
    border-radius: 14px !important;
    padding: 8px 18px !important;
    transition: all 0.15s;
    font-size: 0.85rem !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    background-color: {INDIGO} !important;
    color: #ffffff !important;
    border-bottom: none !important;
}}
[data-baseweb="tab-highlight"] {{ display: none !important; }}
[data-baseweb="tab-border"] {{ display: none !important; }}
[data-baseweb="tab-list"] {{
    background: {CARD_BG} !important;
    border-radius: 20px !important;
    padding: 6px !important;
    gap: 2px !important;
    margin-bottom: 12px !important;
}}

/* ── Header card ── */
.lesko-header-card {{
    background: {CARD_BG};
    border-radius: 20px;
    padding: 16px 22px;
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 12px;
}}
.header-logo {{
    width: 40px; height: 40px;
    background: {INDIGO};
    border-radius: 14px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 500;
    font-size: 1.1rem;
    flex-shrink: 0;
}}
.header-app-name {{
    font-size: 1rem;
    font-weight: 500;
    color: #111827;
    display: block;
    line-height: 1.2;
}}
.header-sub {{
    font-size: 0.7rem;
    color: #6b7280;
    display: block;
    margin-top: 2px;
}}
.header-user-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #f5f7fb;
    padding: 5px 12px 5px 5px;
    border-radius: 999px;
    margin-left: auto;
}}
.header-user-avatar {{
    width: 28px; height: 28px;
    border-radius: 50%;
    background: {YELLOW};
    color: #5a4400;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.68rem;
    font-weight: 500;
}}
.header-user-name {{
    font-size: 0.82rem;
    font-weight: 500;
    color: #111827;
}}

/* ── KPI Row A cards (icon top-left, label top-right, value bottom) ── */
.kpi-card {{
    background: {CARD_BG};
    border-radius: 18px;
    padding: 20px 22px;
    min-height: 110px;
    margin-bottom: 4px;
}}
.kpi-card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}}
.kpi-icon {{
    width: 38px; height: 38px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1rem;
    font-weight: 500;
    flex-shrink: 0;
}}
.kpi-label {{
    font-size: 0.82rem;
    color: #6b7280;
    font-weight: 500;
}}
.kpi-value {{
    font-size: 2.4rem;
    font-weight: 600;
    color: #111827;
    line-height: 1;
}}

/* ── KPI Row B plain cards ── */
.kpi-b-card {{
    background: {CARD_BG};
    border-radius: 18px;
    padding: 20px 22px;
    min-height: 100px;
    margin-bottom: 4px;
}}
.kpi-b-label {{
    font-size: 0.82rem;
    color: #6b7280;
    font-weight: 500;
    margin-bottom: 6px;
}}
.kpi-b-value {{
    font-size: 2rem;
    font-weight: 600;
    color: #111827;
    line-height: 1;
}}

/* ── KPI Goal card ── */
.kpi-goal-card {{
    background: {INDIGO};
    border-radius: 18px;
    padding: 20px 22px;
    min-height: 100px;
    margin-bottom: 4px;
}}
.kpi-goal-label {{
    font-size: 0.82rem;
    color: #c4c8e6;
    font-weight: 500;
    margin-bottom: 8px;
}}
.kpi-goal-row {{
    display: flex;
    align-items: baseline;
    gap: 4px;
    margin-bottom: 10px;
}}
.kpi-goal-value {{
    font-size: 2rem;
    font-weight: 600;
    color: white;
    line-height: 1;
}}
.kpi-goal-total {{
    font-size: 0.75rem;
    color: #c4c8e6;
}}
.kpi-goal-bar-bg {{
    background: rgba(255,255,255,0.25);
    border-radius: 999px;
    height: 4px;
    overflow: hidden;
}}
.kpi-goal-bar-fill {{
    background: {YELLOW};
    border-radius: 999px;
    height: 4px;
}}

/* ── Section card (tickets list) ── */
.section-card {{
    background: {CARD_BG};
    border-radius: 20px;
    padding: 18px 18px 10px;
    margin-top: 14px;
}}
.section-card-title {{
    font-size: 1rem;
    font-weight: 500;
    color: #111827;
    margin-bottom: 14px;
}}
.section-card-count {{
    color: #6b7280;
    font-weight: 400;
}}

/* ── Member initials avatar ── */
.mem-avatar {{
    width: 24px; height: 24px;
    border-radius: 8px;
    background: {INDIGO};
    color: white;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6rem;
    font-weight: 500;
    flex-shrink: 0;
}}
.mem-avatar-green  {{ background: {GREEN};   color: white; }}
.mem-avatar-blue   {{ background: {BLUE};    color: white; }}
.mem-avatar-red    {{ background: {RED};     color: white; }}
.mem-avatar-yellow {{ background: {YELLOW};  color: #5a4400; }}

/* ── Domain icon circle ── */
.domain-circle {{
    width: 26px; height: 26px;
    border-radius: 50%;
    background: {GREEN};
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    flex-shrink: 0;
}}

/* ── Status badges (exact mockup colors) ── */
.badge {{
    display: inline-block;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 0.875rem;
    font-weight: 500;
    white-space: nowrap;
}}
.badge-open           {{ background: #e1edfb; color: #1d4e8c; }}
.badge-answered       {{ background: #d6f0d6; color: #1f6a1f; }}
.badge-closed         {{ background: #d6f0d6; color: #1f6a1f; }}
.badge-cancelled      {{ background: #fde0e0; color: #8a1f1f; }}
.badge-not_a_question {{ background: #f0f0f0; color: #666;     }}

/* ── Urgency pills (exact mockup colors) ── */
.urg-pill {{ display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 0.875rem; font-weight: 500; white-space: nowrap; }}
.urg-normal   {{ background: #e6f4e6; color: #1f6a1f; }}
.urg-urgent   {{ background: #fdf3d4; color: #7a5f00; }}
.urg-critical {{ background: #fde0e0; color: #8a1f1f; }}

/* ── Assign pill ── */
.assign-pill {{
    display: inline-block;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 500;
    background: #eef0f9;
    color: {INDIGO};
    white-space: nowrap;
}}
.assign-empty {{
    display: inline-block;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 500;
    background: white;
    color: #6b7280;
    border: 1px dashed #c4c8d4;
    white-space: nowrap;
}}

/* ── Open ticket button ── */
.open-btn {{
    width: 24px; height: 24px;
    border-radius: 50%;
    background: {INDIGO};
    color: white;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    cursor: pointer;
}}

/* ── Table column headers ── */
.tbl-header {{
    font-size: 0.62rem;
    font-weight: 500;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding-bottom: 8px;
}}

/* ── Buttons ── */
button[data-testid="baseButton-primary"] {{
    background-color: #7b82c9 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 500 !important;
}}
button[data-testid="baseButton-primary"]:hover {{
    background-color: {INDIGO} !important;
}}
button[data-testid="baseButton-secondary"] {{
    background-color: #eef0fb !important;
    color: {INDIGO} !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 500 !important;
}}
button[data-testid="baseButton-secondary"]:hover {{
    background-color: #dde0f5 !important;
}}

/* ── Metric cards (reports tab) ── */
[data-testid="metric-container"] {{
    background: {CARD_BG};
    border-left: 4px solid {INDIGO};
    border-radius: 10px;
    padding: 10px 14px !important;
}}
[data-testid="metric-container"] label {{
    color: #6b7280 !important;
    font-size: 0.8rem !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: #111827 !important;
    font-weight: 500;
}}

/* ── Table header row ── */
.tbl-header {{
    font-size: 0.72rem;
    font-weight: 700;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 0 4px 8px;
    border-bottom: 1px solid #e8eef6;
    margin-bottom: 6px;
}}

/* ── Dividers ── */
hr {{ border-color: #e0e6f0 !important; }}
</style>
""", unsafe_allow_html=True)

# ── Domain icons ───────────────────────────────────────────────────────────────
DOMAIN_ICON = {
    "Pay Debt & Bills":        "💰",
    "Home & Housing Help":     "🏠",
    "Cars & Car Repairs":      "🚗",
    "Healthcare Assistance":   "🏥",
    "Start A Business":        "🚀",
    "Launch A Nonprofit":      "🤲",
    "Boost Your Career":       "💼",
    "Taxes Help Guidance":     "🧾",
    "Find Legal Help":         "⚖️",
    "Family & Children":       "👨‍👩‍👧",
    "Seniors & Disabilities":  "🛡️",
    "Programs for Veterans":   "🎖️",
    "Community Support":       "🤝",
    "Other":                   "📌",
}

STATUS_ICON = {
    "open":            "🔵",
    "closed":          "🟢",
    "cancelled":       "🔴",
    "answered":        "✅",
    "not_a_question":  "⚪",
}
URGENCY_ICON = {
    "normal":   "🟢",
    "urgent":   "🟡",
    "critical": "🔴",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _initials(name: str) -> str:
    parts = (name or "?").split()
    return "".join(p[0].upper() for p in parts[:2]) if parts else "?"

def _avatar_class(name: str) -> str:
    colors = ["mem-avatar-green", "mem-avatar-blue", "mem-avatar-red", "mem-avatar-yellow", ""]
    return colors[hash(name or "") % len(colors)]

def kpi_card(label: str, value, icon_color: str) -> str:
    """KPI Row A — icon top-left, label top-right, big value bottom."""
    return f"""
    <div class="kpi-card">
      <div class="kpi-card-top">
        <div class="kpi-icon" style="background:{icon_color}">●</div>
        <div class="kpi-label">{label}</div>
      </div>
      <div class="kpi-value">{value:,}</div>
    </div>"""

def kpi_b_card(label: str, value) -> str:
    """KPI Row B — plain label + value."""
    return f"""
    <div class="kpi-b-card">
      <div class="kpi-b-label">{label}</div>
      <div class="kpi-b-value">{value}</div>
    </div>"""

def goal_card(answered: int, goal: int) -> str:
    pct = min(100, round(answered / goal * 100)) if goal > 0 else 0
    return f"""
    <div class="kpi-goal-card">
      <div class="kpi-goal-label">Goal progress</div>
      <div class="kpi-goal-row">
        <div class="kpi-goal-value">{answered}</div>
        <div class="kpi-goal-total">/ {goal}</div>
      </div>
      <div class="kpi-goal-bar-bg">
        <div class="kpi-goal-bar-fill" style="width:{pct}%"></div>
      </div>
    </div>"""


# ── Auth ───────────────────────────────────────────────────────────────────────
if not st.user.is_logged_in:
    st.markdown(f"""
    <div style="
        display:flex; flex-direction:column; align-items:center;
        justify-content:center; min-height:70vh; gap:12px;
    ">
      <div style="
          background:{CARD_BG}; border-radius:24px;
          padding:44px 56px; text-align:center; max-width:420px;
          box-shadow:0 4px 24px rgba(74,82,163,0.13);
      ">
        <div style="
            width:64px; height:64px; border-radius:16px; background:{INDIGO};
            display:inline-flex; align-items:center; justify-content:center;
            font-size:2rem; color:white; font-weight:800; margin-bottom:16px;
        ">L</div>
        <h2 style="margin:0 0 6px; color:#1a1a2e; font-size:1.5rem;">Lesko Help Desk</h2>
        <p style="color:#999; font-size:0.9rem; margin:0 0 28px;">
          Grant support queue — team access only
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button(
            "Sign in with Google",
            on_click=st.login,
            args=("google",),
            use_container_width=True,
            type="primary",
        )
        st.button(
            "Sign in with email",
            on_click=st.login,
            args=("auth0",),
            use_container_width=True,
        )
    st.stop()

user         = st.user
current_user = user.email or user.name or ""

# ── Session state defaults ─────────────────────────────────────────────────────
if "member_id_filter" not in st.session_state:
    st.session_state.member_id_filter = ""

# ── Sidebar (user account + filters) ──────────────────────────────────────────
with st.sidebar:
    # User account
    avatar_url = getattr(user, "picture", None)
    name       = getattr(user, "name",    None) or current_user
    email      = getattr(user, "email",   None) or ""

    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; padding:4px 0 12px;">
      <div class="mem-avatar {_avatar_class(name)}">{_initials(name)}</div>
      <div>
        <div style="font-weight:700; font-size:0.9rem; color:#1a1a2e;">{name}</div>
        <div style="font-size:0.72rem; color:#999;">{email}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign out", use_container_width=True):
        st.logout()

    st.divider()

    # ── Filters ───────────────────────────────────────────────────────────────
    st.markdown('<p style="font-size:0.72rem;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">Filters</p>', unsafe_allow_html=True)

    today = datetime.date.today()

    # 1. Status
    _status_opts = ["All"] + config.TICKET_STATUSES
    filter_status = st.selectbox(
        "Status",
        _status_opts,
        index=_status_opts.index("open"),
        format_func=lambda s: s if s == "All" else s.replace("_", " ").title(),
    )

    # 2. Date range
    date_range_option = st.radio(
        "Date Range",
        ["All", "Today", "This Week", "This Month", "Custom"],
        horizontal=True,
    )
    if date_range_option == "All":
        date_from, date_to = None, None
    elif date_range_option == "Today":
        date_from, date_to = today, today
    elif date_range_option == "This Week":
        date_from = today - datetime.timedelta(days=today.weekday())
        date_to   = today
    elif date_range_option == "This Month":
        date_from = today.replace(day=1)
        date_to   = today
    else:
        custom_range = st.date_input(
            "Select Range",
            value=(today - datetime.timedelta(days=7), today),
        )
        if isinstance(custom_range, (list, tuple)) and len(custom_range) == 2:
            date_from, date_to = custom_range
        else:
            date_from = date_to = custom_range

    # 3. Assigned To
    team_members = bq_client.get_team_members()
    filter_assignee = st.selectbox(
        "Grant Coach",
        ["All"] + team_members,
    )

    # 4. Member ID
    filter_member_id = st.text_input(
        "Member ID",
        value=st.session_state.member_id_filter,
    )

    # 5. Urgency (pill buttons)
    filter_urgency = st.pills(
        "Urgency",
        options=["All", "Normal", "Urgent", "Critical"],
        default="All",
    )

    # 6. Domain
    filter_domain = st.selectbox(
        "Domain",
        ["All"] + config.DOMAINS,
    )

    st.divider()
    if st.button("🔄 Refresh data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()


# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_tickets(status, date_from, date_to, assignee, member_id, urgency, domain):
    return bq_client.get_tickets(
        status=status,
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        assignee=assignee,
        member_id=member_id or None,
        urgency=urgency,
        domain=domain,
    )

@st.cache_data(ttl=300)
def load_open_stats():
    return bq_client.get_open_stats()

@st.cache_data(ttl=300)
def load_daily_stats():
    return bq_client.get_daily_stats()

@st.cache_data(ttl=300)
def load_report(report_type: str, date_from: str, date_to: str):
    return bq_client.get_report_data(report_type, date_from, date_to)


# ══════════════════════════════════════════════════════════════════════════════
# TICKET DETAIL DIALOG
# ══════════════════════════════════════════════════════════════════════════════
@st.dialog("Ticket Detail", width="large")
def show_ticket_dialog(content_id: str):
    ticket = bq_client.get_ticket_detail(content_id)
    if not ticket:
        st.warning("Ticket not found.")
        return

    status_icon  = STATUS_ICON.get(ticket.get("ticket_status"), "⚪")
    urgency_icon = URGENCY_ICON.get(ticket.get("urgency"), "⚪")
    content_type = ticket.get("content_type") or "—"
    domain_icon  = DOMAIN_ICON.get(ticket.get("domain") or "", "")

    # Header card
    _urg        = (ticket.get("urgency") or "normal").lower()
    _urg_colors = {"normal": ("#d6f0d6","#1f6a1f"), "urgent": ("#fdf3d4","#7a5f00"), "critical": ("#fde0e0","#8a1f1f")}
    _urg_bg, _urg_fg = _urg_colors.get(_urg, _urg_colors["normal"])
    _status     = (ticket.get("ticket_status") or "open").lower()
    _domain_str = f"{domain_icon} {ticket.get('domain')}" if domain_icon else ""
    _permalink  = ticket.get("member_permalink") or ""
    _state      = ticket.get("member_state") or "—"
    _city       = ticket.get("member_city") or "—"
    _mid        = ticket.get("member_id") or "—"
    _posted     = str(ticket.get("created_at", "—"))[:16]

    st.markdown(f"""
<div style="margin:-1rem -1rem 0 -1rem;padding:16px 20px 14px;background:#f7f9fc;border-bottom:1px solid #e8eef6;">
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
    <span style="font-size:1.1rem;font-weight:700;color:#1a1a2e">{ticket.get('member_name','Unknown')}</span>
    <span class="badge badge-{_status}">{_status.replace('_',' ').capitalize()}</span>
    <span style="background:{_urg_bg};color:{_urg_fg};padding:3px 9px;border-radius:999px;font-size:0.68rem;font-weight:500">{_urg.capitalize()}</span>
    <span style="font-size:0.78rem;color:#6b7280">{content_type}</span>
    {f'<span style="font-size:0.78rem;color:#6b7280">{_domain_str}</span>' if _domain_str else ""}
    {f'<a href="{_permalink}" target="_blank" style="margin-left:auto;font-size:0.75rem;color:{INDIGO};text-decoration:none">↗ MN Profile</a>' if _permalink else ""}
  </div>
  <div style="display:flex;gap:24px;flex-wrap:wrap">
    <span style="font-size:0.75rem;color:#6b7280"><span style="font-weight:600;color:#374151">State</span>&nbsp; {_state}</span>
    <span style="font-size:0.75rem;color:#6b7280"><span style="font-weight:600;color:#374151">City</span>&nbsp; {_city}</span>
    <span style="font-size:0.75rem;color:#6b7280"><span style="font-weight:600;color:#374151">Member ID</span>&nbsp; {_mid}</span>
    <span style="font-size:0.75rem;color:#6b7280"><span style="font-weight:600;color:#374151">Posted</span>&nbsp; {_posted}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Full thread
    thread_id = ticket.get("thread_id") or content_id
    with st.spinner("Loading thread…"):
        thread = bq_client.get_thread(thread_id)

    if not thread.empty:
        # ── Root post ─────────────────────────────────────────────────────────
        root = thread[thread["content_type"] == "post"]
        if not root.empty:
            r = root.iloc[0]
            is_ticket = r["content_id"] == content_id
            st.markdown("**Original Post**")
            st.markdown(f"""
<div style="background:#f0f4ff;border-left:4px solid {INDIGO};border-radius:12px;padding:14px 16px;margin-bottom:16px">
  <div style="font-weight:700;font-size:0.95rem;color:#1a1a2e;margin-bottom:2px">
    {r['author_name']}
    {"&nbsp;<span style='font-size:0.72rem;background:#4a52a3;color:white;padding:2px 7px;border-radius:999px'>this ticket</span>" if is_ticket else ""}
  </div>
  <div style="font-size:0.72rem;color:#6b7280;margin-bottom:10px">{str(r['created_at'])[:16]}</div>
  <div style="font-size:0.9rem;color:#111827;line-height:1.55">{r['body'] or '<em>empty</em>'}</div>
  {"<div style='margin-top:8px'><a href='" + r['permalink'] + "' target='_blank' style='font-size:0.75rem;color:#4a52a3'>↗ View on Mighty Networks</a></div>" if r.get('permalink') else ""}
</div>
""", unsafe_allow_html=True)

        # ── Comments ──────────────────────────────────────────────────────────
        comments = thread[thread["content_type"] == "comment"]
        if not comments.empty:
            st.markdown(f"**Comments ({len(comments)})**")
            for _, item in comments.iterrows():
                is_current = item["content_id"] == content_id
                is_team    = item["author_type"] == "team"
                depth      = int(item.get("depth") or 1)
                indent_px  = (depth - 1) * 20
                role = "assistant" if is_team else "user"
                with st.chat_message(role):
                    label = f"{'　' * (depth - 1)}**{item['author_name']}** · {str(item['created_at'])[:16]}"
                    if is_current:
                        label += " 📌 *this ticket*"
                    st.markdown(label)
                    st.markdown(item["body"] or "_(empty)_")
                    if item.get("permalink"):
                        st.markdown(f"[↗ View]({item['permalink']})")

    st.divider()

    # Editable fields
    st.markdown("**Update Ticket**")
    can_edit = ticket.get("ticket_status") != "closed"

    c1, c2 = st.columns(2)
    with c1:
        all_statuses   = config.TICKET_STATUSES + config.FEEDBACK_STATUSES
        current_status = ticket.get("manual_status") or ticket.get("ticket_status") or "new"
        if current_status not in all_statuses:
            current_status = "new"
        new_status = st.selectbox(
            "Status",
            all_statuses,
            index=all_statuses.index(current_status),
            disabled=not can_edit,
            key=f"status_{content_id}",
            format_func=lambda s: f"{STATUS_ICON.get(s, '')} {s.replace('_', ' ').title()}",
        )
    with c2:
        assignee_options = ["— unassigned —"] + team_members
        current_assignee = ticket.get("assigned_to") or "— unassigned —"
        if current_assignee not in assignee_options:
            current_assignee = "— unassigned —"
        new_assignee = st.selectbox(
            "Grant Coach",
            assignee_options,
            index=assignee_options.index(current_assignee),
            key=f"assignee_{content_id}",
        )

    # Override checkbox — only shown when an assignee is selected
    override_assignment = False
    if new_assignee != "— unassigned —" and can_edit:
        override_assignment = st.checkbox(
            f"Set as permanent Grant Coach for **{ticket.get('member_name', 'this member')}**",
            value=False,
            help="Overrides the automatic assignment rule — all future tickets from this member will go to this Grant Coach.",
            key=f"override_{content_id}",
        )

    # Reason field — only shown for feedback statuses
    feedback_reason = None
    if new_status in config.FEEDBACK_STATUSES:
        feedback_reason = st.text_area(
            "Reason",
            value=ticket.get("feedback_reason") or "",
            placeholder="Explain why this is / is not a question — this trains the AI classifier.",
            key=f"reason_{content_id}",
            height=80,
        )

    c3, c4 = st.columns(2)
    with c3:
        domain_options = ["— unset —"] + config.DOMAINS
        current_domain = ticket.get("domain") or "— unset —"
        if current_domain not in domain_options:
            current_domain = "— unset —"
        new_domain = st.selectbox(
            "Domain",
            domain_options,
            index=domain_options.index(current_domain),
            key=f"domain_{content_id}",
        )

    if can_edit:
        if st.button("💾 Save changes", key=f"save_{content_id}"):
            assignee_val = "" if new_assignee == "— unassigned —" else new_assignee
            domain_val   = "" if new_domain   == "— unset —"      else new_domain
            bq_client.update_ticket_meta(
                content_id, new_status, assignee_val, domain_val,
                feedback_reason=feedback_reason,
            )
            if override_assignment and assignee_val:
                bq_client.set_member_assignment_override(
                    ticket["member_id"], assignee_val, current_user
                )
            st.cache_data.clear()
            st.success("Saved." if not override_assignment else "Saved — permanent Grant Coach updated.")
    else:
        st.caption("⚠️ Ticket is closed — status locked.")

    st.divider()

    # Answer entry — posts to Mighty Networks via API
    st.markdown("**Post an Answer to Mighty Networks**")
    _mn_key = bq_client.get_mn_api_key(current_user) if current_user else None
    if not _mn_key:
        st.warning("No Mighty Networks API key set. Add yours in the ⚙️ Settings tab.")
    else:
        _post_id = (ticket.get("thread_id") or content_id).replace("post_", "")
        answer_body = st.text_area(
            "Answer", key=f"answer_{content_id}",
            label_visibility="collapsed", height=180,
        )
        if st.button("Post Answer to MN", key=f"post_answer_{content_id}", type="primary"):
            if answer_body.strip():
                try:
                    bq_client.post_mn_comment(_post_id, answer_body.strip(), _mn_key)
                    st.session_state[f"answer_{content_id}"] = ""
                    st.cache_data.clear()
                    st.success("Answer posted to Mighty Networks.")
                except Exception as e:
                    st.error(f"Failed to post: {e}")
            else:
                st.warning("Answer cannot be empty.")

    st.divider()

    # Internal comment thread
    st.markdown("**Internal Thread**")
    comments = bq_client.get_comments(content_id)
    if comments.empty:
        st.caption("No internal comments yet.")
    else:
        for _, c in comments.iterrows():
            with st.chat_message("assistant"):
                st.markdown(f"**{c['author']}** · {str(c['created_at'])[:16]}")
                st.markdown(c["body"])

    st.markdown("**Add Internal Comment**")
    if not current_user:
        st.warning("Set the `LESKO_USER` env var to post comments.")
    else:
        comment_body = st.text_area(
            "Comment", key=f"comment_{content_id}", label_visibility="collapsed", height=140,
        )
        if st.button("Post Comment", key=f"post_comment_{content_id}"):
            if comment_body.strip():
                bq_client.post_comment(content_id, current_user, comment_body.strip())
                st.session_state[f"comment_{content_id}"] = ""
                st.success("Comment posted.")
            else:
                st.warning("Comment cannot be empty.")

    st.divider()

    # Placeholders
    ph1, ph2 = st.columns(2)
    ph1.button(
        "🤖 AI-generated answer", disabled=True,
        help="Coming soon", key=f"ai_{content_id}",
        use_container_width=True,
    )
    ph2.button(
        "📋 Predefined answers", disabled=True,
        help="Coming soon", key=f"pre_{content_id}",
        use_container_width=True,
    )

    with st.expander("📋 Call Sheet Report"):
        st.caption("Prompt template wiring coming soon.")
        st.text_input("State",  value=ticket.get("member_state") or "", disabled=True)
        st.text_input("Domain", value=ticket.get("domain") or "",       disabled=True)
        st.button("Generate Report", disabled=True, help="Coming soon", key=f"callsheet_{content_id}")

    with st.expander(f"📋 Member history ({ticket.get('member_name', '')})"):
        history = bq_client.get_member_history(
            ticket["member_id"], exclude_content_id=ticket["content_id"]
        )
        if history.empty:
            st.write("No other tickets from this member.")
        else:
            for _, h in history.iterrows():
                h_icon = STATUS_ICON.get(h["ticket_status"], "⚪")
                st.markdown(f"{h_icon} `{str(h['created_at'])[:10]}` — {h['body_preview']}")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP DIALOG — multiple comments from same member in same thread
# ══════════════════════════════════════════════════════════════════════════════
@st.dialog("Member Thread", width="large")
def show_group_dialog(thread_id: str, member_id: str, member_name: str):
    _OPEN = {"open", "new", "assigned"}
    _URG_COLORS = {
        "normal":   ("#d6f0d6", "#1f6a1f"),
        "urgent":   ("#fdf3d4", "#7a5f00"),
        "critical": ("#fde0e0", "#8a1f1f"),
    }

    group_tix = bq_client.get_member_thread_tickets(thread_id, member_id)
    if group_tix.empty:
        st.warning("No tickets found.")
        return

    open_tix = group_tix[group_tix["ticket_status"].isin(_OPEN)]
    done_tix = group_tix[~group_tix["ticket_status"].isin(_OPEN)]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin:-1rem -1rem 0 -1rem;padding:14px 20px 12px;background:#f7f9fc;border-bottom:1px solid #e8eef6">
  <span style="font-size:1.05rem;font-weight:700;color:#1a1a2e">{member_name}</span>
  <span style="font-size:0.8rem;color:#6b7280;margin-left:10px">{len(open_tix)} open comment{"s" if len(open_tix) != 1 else ""} · {len(done_tix)} handled</span>
</div>
""", unsafe_allow_html=True)

    # ── Original post (context) ───────────────────────────────────────────────
    with st.spinner("Loading thread…"):
        thread = bq_client.get_thread(thread_id)

    # ── Full thread ───────────────────────────────────────────────────────────
    if not thread.empty:
        # Collect content_ids that belong to this member's open tickets
        _open_ids = set(open_tix["content_id"].tolist())

        with st.expander("📄 Full thread", expanded=True):
            with st.container(height=520):
                for _, item in thread.iterrows():
                    is_member_ticket = item["content_id"] in _open_ids
                    is_team = item["author_type"] == "team"
                    depth   = int(item.get("depth") or 0)
                    role    = "assistant" if is_team else "user"
                    with st.chat_message(role):
                        label = f"{'　' * depth}**{item['author_name']}** · {str(item['created_at'])[:16]}"
                        if is_member_ticket:
                            label += " 📌 *open ticket*"
                        st.markdown(label)
                        st.markdown(item["body"] or "_(empty)_")
                        if item.get("permalink"):
                            st.markdown(f"[↗ View]({item['permalink']})")

    st.divider()

    # ── Open comments ─────────────────────────────────────────────────────────
    if open_tix.empty:
        st.info("All comments in this thread are already handled.")
    else:
        all_statuses = config.TICKET_STATUSES + config.FEEDBACK_STATUSES
        _assignee_opts = ["— unassigned —"] + team_members
        _domain_opts   = ["— unset —"] + config.DOMAINS

        # Bulk controls
        st.markdown(f"**Apply to all {len(open_tix)} open comments**")
        bc1, bc2, bc3 = st.columns(3)
        bulk_status = bc1.selectbox(
            "Status", all_statuses,
            key=f"bulk_status_{thread_id}_{member_id}",
            format_func=lambda s: f"{STATUS_ICON.get(s,'')} {s.replace('_',' ').title()}",
        )
        bulk_coach = bc2.selectbox(
            "Grant Coach", _assignee_opts,
            key=f"bulk_coach_{thread_id}_{member_id}",
        )
        bulk_domain = bc3.selectbox(
            "Domain", _domain_opts,
            key=f"bulk_domain_{thread_id}_{member_id}",
        )
        if st.button("💾 Save to all open comments", type="primary", key=f"bulk_save_{thread_id}_{member_id}"):
            _av = "" if bulk_coach  == "— unassigned —" else bulk_coach
            _dv = "" if bulk_domain == "— unset —"      else bulk_domain
            for _, t in open_tix.iterrows():
                bq_client.update_ticket_meta(t["content_id"], bulk_status, _av, _dv)
            st.cache_data.clear()
            st.success(f"Saved {len(open_tix)} comments.")

        st.divider()

        # Individual open comments
        st.markdown(f"**Open comments ({len(open_tix)})**")
        for _, t in open_tix.iterrows():
            urg = (t.get("urgency") or "normal").lower()
            urg_bg, urg_fg = _URG_COLORS.get(urg, _URG_COLORS["normal"])
            st.markdown(f"""
<div style="background:#fff;border:1px solid #e8eef6;border-radius:12px;padding:12px 14px;margin-bottom:6px">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
    <span class="badge badge-open">open</span>
    <span style="background:{urg_bg};color:{urg_fg};padding:2px 8px;border-radius:999px;font-size:0.68rem;font-weight:500">{urg.capitalize()}</span>
    <span style="font-size:0.72rem;color:#9ca3af">{str(t['created_at'])[:16]}</span>
    {f'<a href="{t["permalink"]}" target="_blank" style="margin-left:auto;font-size:0.72rem;color:{INDIGO};text-decoration:none">↗</a>' if t.get("permalink") else ""}
  </div>
  <div style="font-size:0.88rem;color:#111827;line-height:1.55">{t.get("body_preview") or "<em>(empty)</em>"}</div>
</div>""", unsafe_allow_html=True)

            with st.expander("Reply & settings for this comment"):
                # ── Post answer to MN ──────────────────────────────────────
                _mn_key = bq_client.get_mn_api_key(current_user) if current_user else None
                if _mn_key:
                    _pid = thread_id.replace("post_", "")
                    ans = st.text_area(
                        "Post Answer to Mighty Networks",
                        key=f"grp_ans_{t['content_id']}",
                        height=100,
                        placeholder="Type your answer here…",
                    )
                    if st.button("Post Answer to MN", key=f"grp_post_{t['content_id']}", type="primary"):
                        if ans.strip():
                            try:
                                bq_client.post_mn_comment(_pid, ans.strip(), _mn_key)
                                st.session_state[f"grp_ans_{t['content_id']}"] = ""
                                st.success("Answer posted to Mighty Networks.")
                            except Exception as e:
                                st.error(f"Failed: {e}")
                        else:
                            st.warning("Answer cannot be empty.")
                else:
                    st.caption("No MN API key — add yours in ⚙️ Settings.")

                st.divider()

                # ── Status & coach override ────────────────────────────────
                ov1, ov2 = st.columns(2)
                _cur_status = t.get("ticket_status") or "open"
                _cur_status = _cur_status if _cur_status in all_statuses else "open"
                _cur_coach  = t.get("assigned_to") or "— unassigned —"
                if _cur_coach not in _assignee_opts:
                    _cur_coach = "— unassigned —"
                ov_status = ov1.selectbox(
                    "Status", all_statuses,
                    index=all_statuses.index(_cur_status),
                    key=f"ov_status_{t['content_id']}",
                    format_func=lambda s: f"{STATUS_ICON.get(s,'')} {s.replace('_',' ').title()}",
                )
                ov_coach = ov2.selectbox(
                    "Grant Coach", _assignee_opts,
                    index=_assignee_opts.index(_cur_coach),
                    key=f"ov_coach_{t['content_id']}",
                )
                if st.button("💾 Save this comment", key=f"ov_save_{t['content_id']}"):
                    _av2 = "" if ov_coach == "— unassigned —" else ov_coach
                    bq_client.update_ticket_meta(t["content_id"], ov_status, _av2, "")
                    st.cache_data.clear()
                    st.success("Saved.")

    # ── Done comments (grayed out) ────────────────────────────────────────────
    if not done_tix.empty:
        st.divider()
        st.markdown(f"**Already handled ({len(done_tix)})**")
        for _, t in done_tix.iterrows():
            _s = (t.get("ticket_status") or "").lower()
            st.markdown(f"""
<div style="background:#f9fafb;border:1px solid #f0f0f0;border-radius:10px;padding:10px 14px;margin-bottom:6px;opacity:0.6">
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:4px">
    <span class="badge badge-{_s}">{_s.replace("_"," ").capitalize()}</span>
    <span style="font-size:0.72rem;color:#9ca3af">{str(t['created_at'])[:16]}</span>
  </div>
  <div style="font-size:0.84rem;color:#6b7280;line-height:1.5">{t.get("body_preview") or "<em>(empty)</em>"}</div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="lesko-header-card">
  <div class="header-logo">L</div>
  <div style="flex:1;">
    <span class="header-app-name">Lesko Help Desk</span>
    <span class="header-sub">Grant support workspace</span>
  </div>
  <div class="header-user-pill">
    <div class="header-user-avatar">{_initials(name)}</div>
    <span class="header-user-name">{name.split()[0] if name else ''}</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab_main, tab_reports, tab_train, tab_settings, tab_admin = st.tabs(["🎫 Tickets", "📊 Reports", "🤖 Train AI", "⚙️ Settings", "👥 Admin"])

_QUICK_STATUSES = ["open", "answered", "closed", "cancelled"]

def _quick_status_save(content_id: str, row_dict: dict):
    new_status = st.session_state.get(f"qs_{content_id}")
    if not new_status or new_status == row_dict.get("ticket_status"):
        return
    assignee = row_dict.get("assigned_to") or ""
    domain   = row_dict.get("domain") or ""
    bq_client.update_ticket_meta(content_id, new_status, assignee, domain)
    # If closed/cancelled with no prior team comment → log as potential false positive
    if new_status in ("closed", "cancelled") and not row_dict.get("team_commented"):
        bq_client.log_event(
            level="INFO",
            source="closed_without_comment",
            message=f"Ticket {content_id} closed as '{new_status}' without team comment — possible classifier false positive",
            detail=f"member_id={row_dict.get('member_id')} domain={row_dict.get('domain')}",
        )
    st.cache_data.clear()


# ── MAIN TAB ──────────────────────────────────────────────────────────────────
with tab_main:
    tickets     = load_tickets(
        filter_status, date_from, date_to,
        filter_assignee, filter_member_id,
        filter_urgency, filter_domain,
    )
    open_stats  = load_open_stats()
    daily_stats = load_daily_stats()

    # ── KPI Row A ─────────────────────────────────────────────────────────────
    a1, a2, a3, a4 = st.columns(4)
    a1.markdown(kpi_card("Open",     int(open_stats.get("open",     0)), "#2d6ee0"), unsafe_allow_html=True)
    a2.markdown(kpi_card("Normal",   int(open_stats.get("normal",   0)), "#2e9b2e"), unsafe_allow_html=True)
    a3.markdown(kpi_card("Urgent",   int(open_stats.get("urgent",   0)), "#f5c520"), unsafe_allow_html=True)
    a4.markdown(kpi_card("Critical", int(open_stats.get("critical", 0)), "#e03c3c"), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    # ── KPI Row B ─────────────────────────────────────────────────────────────
    answered_today = int(daily_stats.get("answered_today", 0))
    goal           = int(daily_stats.get("goal", config.DAILY_GOAL))
    b1, b2, b3, b4 = st.columns(4)
    b1.markdown(kpi_b_card("In today",        int(daily_stats.get("in_today", 0))),   unsafe_allow_html=True)
    b2.markdown(kpi_b_card("Answered today",  answered_today),                         unsafe_allow_html=True)
    b3.markdown(kpi_b_card("Daily avg (30d)", daily_stats.get("daily_avg", 0)),        unsafe_allow_html=True)
    b4.markdown(goal_card(answered_today, goal),                                       unsafe_allow_html=True)

    # ── Ticket list ───────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-card-title" style="padding:6px 0 10px">Tickets ({len(tickets)})</div>', unsafe_allow_html=True)

    if tickets.empty:
        st.info("No tickets match the current filters.")
    else:
        _OPEN_S   = {"open", "new", "assigned"}
        _URG_RANK = {"critical": 2, "urgent": 1, "normal": 0}
        _URG_NAME = {2: "critical", 1: "urgent", 0: "normal"}

        # Build group key: (member_id, thread_id) when thread exists, else per-ticket
        def _gk(r):
            tid = r.get("thread_id") or ""
            return f"{r['member_id']}|{tid}" if tid else str(r["content_id"])

        tickets["_gk"] = tickets.apply(_gk, axis=1)

        # Collect ordered groups (preserves created_at DESC ordering)
        seen_gk: dict = {}
        for idx, row in tickets.iterrows():
            gk = row["_gk"]
            seen_gk.setdefault(gk, []).append(idx)

        # Table header
        h0, h1, h2, h3, h4, h5, h6 = st.columns([0.7, 1.5, 3.5, 1, 1.1, 0.4, 0.35])
        for col, label in zip(
            [h0, h1, h2, h3, h4, h5, h6],
            ["Coach", "Member", "Question", "Urgency", "Status", "Link", ""],
        ):
            col.markdown(f'<span class="tbl-header">{label}</span>', unsafe_allow_html=True)

        for gk, indices in seen_gk.items():
            grp = tickets.loc[indices]
            row = grp.iloc[0]
            c0, c1, c2, c3, c4, c5, c6 = st.columns([0.7, 1.5, 3.5, 1, 1.1, 0.4, 0.35])

            # Coach initials
            _ca = row.get("assigned_to") or ""
            c0.markdown(
                f'<div style="text-align:center;font-size:0.85rem;font-weight:600;color:#4a52a3;padding-top:6px">'
                f'{"·" if not _ca else _initials(_ca)}</div>',
                unsafe_allow_html=True,
            )

            # Member name button
            mem_name = row["member_name"] or "Unknown"
            if c1.button(mem_name, key=f"member_{gk}", use_container_width=True):
                st.session_state.member_id_filter = str(row["member_id"])
                st.rerun()
            c1.caption(str(row["created_at"])[:10])

            if len(grp) == 1:
                # ── Single ticket row ──────────────────────────────────────────
                domain_icon  = DOMAIN_ICON.get(row.get("domain") or "", "")
                preview_text = str(row["body_preview"] or "")[:110]
                if domain_icon:
                    c2.markdown(
                        f'<span class="domain-circle">{domain_icon}</span> <small>{preview_text}</small>',
                        unsafe_allow_html=True,
                    )
                else:
                    c2.caption(preview_text)

                urg = (row.get("urgency") or "").lower()
                c3.markdown(f'<span class="urg-pill urg-{urg}">{urg.capitalize() or "—"}</span>', unsafe_allow_html=True)

                # Quick status dropdown
                _cur_s = (row.get("ticket_status") or "open")
                _cur_s = _cur_s if _cur_s in _QUICK_STATUSES else "open"
                c4.selectbox(
                    "Status",
                    _QUICK_STATUSES,
                    index=_QUICK_STATUSES.index(_cur_s),
                    key=f"qs_{row['content_id']}",
                    on_change=_quick_status_save,
                    args=(row["content_id"], row.to_dict()),
                    label_visibility="collapsed",
                )

                permalink = row.get("permalink") or ""
                if permalink:
                    c5.markdown(f"[↗]({permalink})")

                if c6.button("→", key=f"open_{row['content_id']}"):
                    show_ticket_dialog(row["content_id"])

            else:
                # ── Grouped row ────────────────────────────────────────────────
                n_open  = int(grp["ticket_status"].isin(_OPEN_S).sum())
                worst   = _URG_NAME[int(grp["urgency"].map(lambda u: _URG_RANK.get(u, 0)).max())]
                domain_icon = DOMAIN_ICON.get(row.get("domain") or "", "")

                _di_html = f'<span class="domain-circle">{domain_icon}</span> ' if domain_icon else ""
                c2.markdown(
                    f'{_di_html}<small><strong>{len(grp)} comments</strong> in thread · {n_open} open</small>',
                    unsafe_allow_html=True,
                )
                c3.markdown(f'<span class="urg-pill urg-{worst}">{worst.capitalize()}</span>', unsafe_allow_html=True)
                c4.markdown(f'<span class="badge badge-open">{n_open} open</span>', unsafe_allow_html=True)

                permalink = row.get("permalink") or ""
                if permalink:
                    c5.markdown(f"[↗]({permalink})")

                if c6.button("→", key=f"open_grp_{gk}"):
                    show_group_dialog(
                        thread_id=str(row["thread_id"]),
                        member_id=str(row["member_id"]),
                        member_name=mem_name,
                    )

    st.markdown("</div>", unsafe_allow_html=True)


# ── REPORTS TAB ───────────────────────────────────────────────────────────────
with tab_reports:
    st.subheader("Reports")

    r1, r2 = st.columns(2)
    with r1:
        r_date_from = st.date_input(
            "From", value=today - datetime.timedelta(days=30), key="r_from"
        )
    with r2:
        r_date_to = st.date_input("To", value=today, key="r_to")

    st.divider()

    st.markdown("#### Volume — Tickets In vs Answered")
    vol = load_report("volume", str(r_date_from), str(r_date_to))
    if not vol.empty:
        st.bar_chart(vol.set_index("date")[["tickets_in", "tickets_closed"]])
    else:
        st.caption("No data for this period.")

    st.divider()

    st.markdown("#### Response Time")
    rt = load_report("response_time", str(r_date_from), str(r_date_to))
    if not rt.empty:
        avg_min = round(rt["minutes_to_response"].mean(), 1)
        med_min = round(rt["minutes_to_response"].median(), 1)
        sla_pct = round((rt["minutes_to_response"] < 1440).mean() * 100, 1)
        rr1, rr2, rr3 = st.columns(3)
        rr1.metric("Avg time to first response", f"{avg_min} min")
        rr2.metric("Median",                     f"{med_min} min")
        rr3.metric("% answered within 24 h",     f"{sla_pct}%")
    else:
        st.caption("No data for this period.")

    st.divider()

    st.markdown("#### Team Productivity — Tickets Closed")
    tp = load_report("team_productivity", str(r_date_from), str(r_date_to))
    if not tp.empty:
        st.bar_chart(tp.set_index("assigned_to")["tickets_closed"])
    else:
        st.caption("No data for this period.")

    st.divider()

    st.markdown("#### Domain Breakdown")
    db = load_report("domain_breakdown", str(r_date_from), str(r_date_to))
    if not db.empty:
        st.bar_chart(db.set_index("domain")["tickets"])
    else:
        st.caption("No data for this period.")

    st.divider()
    st.button("📥 Export to Excel", disabled=True, help="Coming soon")


# ── TRAIN AI TAB ──────────────────────────────────────────────────────────────
with tab_train:
    st.subheader("Train AI")

    if "train_queue" not in st.session_state:
        with st.spinner("Loading review queue…"):
            q_df = bq_client.get_unreviewed_rejects()
            st.session_state.train_queue = q_df.to_dict("records")
            st.session_state.train_idx   = 0

    queue     = st.session_state.train_queue
    idx       = st.session_state.train_idx
    total     = len(queue)
    remaining = total - idx

    if remaining <= 0:
        st.success("All caught up — nothing left to review!")
        if st.button("Reload queue"):
            del st.session_state["train_queue"]
            st.rerun()
    else:
        st.progress(idx / total if total > 0 else 1.0)
        st.caption(f"{idx} reviewed · {remaining} remaining")
        st.divider()

        item = queue[idx]

        meta1, meta2, meta3 = st.columns(3)
        meta1.markdown(f"**Member:** {item.get('member_name') or '—'}")
        meta2.markdown(f"**Type:** {(item.get('content_type') or '—').capitalize()}")
        meta3.markdown(f"**Posted:** {str(item.get('created_at', ''))[:16]}")

        permalink = item.get("permalink") or ""
        if permalink:
            st.markdown(f"[View on MightyNetworks ↗]({permalink})")

        st.divider()
        with st.container(height=100):
            st.markdown(item.get("body") or "_(no content)_")

        st.divider()

        btn_incorrect, btn_correct = st.columns(2)

        if btn_incorrect.button(
            "Incorrect — this IS a question",
            use_container_width=True,
            type="primary",
            key=f"incorrect_{item['content_id']}",
        ):
            bq_client.update_ticket_meta(item["content_id"], "confirmed_question", "")
            st.session_state.train_idx += 1
            st.rerun()

        if btn_correct.button(
            "Correct — not a question",
            use_container_width=True,
            key=f"correct_{item['content_id']}",
        ):
            bq_client.update_ticket_meta(item["content_id"], "not_a_question", "")
            st.session_state.train_idx += 1
            st.rerun()


# ── SETTINGS TAB ──────────────────────────────────────────────────────────────
with tab_settings:
    st.subheader("Your Mighty Networks API Key")
    st.caption(
        "Required to post answers directly to Mighty Networks from the ticket dialog. "
        "Each team member needs their own key. Generate one in your MN admin panel under "
        "**Admin → Settings → API Keys**."
    )

    @st.dialog("Add Mighty Networks API Key")
    def api_key_dialog():
        st.caption("Your key is stored securely in BigQuery and never shown again.")
        new_key = st.text_input("Paste your API key", type="password", placeholder="mn_live_...")
        c1, c2 = st.columns(2)
        if c1.button("Save", type="primary", use_container_width=True):
            if new_key.strip():
                bq_client.save_mn_api_key(current_user, new_key.strip())
                st.success("Saved.")
                st.rerun()
            else:
                st.warning("Please enter a key.")
        if c2.button("Cancel", use_container_width=True):
            st.rerun()

    _has_key = bq_client.get_mn_api_key(current_user) is not None if current_user else False
    if _has_key:
        st.success("✓ API key configured")
        if st.button("Replace key"):
            api_key_dialog()
    else:
        st.warning("No API key set")
        if st.button("Add API Key", type="primary"):
            api_key_dialog()

    st.divider()
    st.subheader("Classifier Prompt Settings")
    st.caption(
        "The AI classifier reads every community post and decides whether it "
        "needs a staff response. The prompt below drives that decision. It is "
        "updated automatically every week by the Dataform pipeline when enough "
        "team feedback has been collected."
    )

    @st.cache_data(ttl=300)
    def load_prompt_history():
        return bq_client.get_prompt_history()

    prompt_history = load_prompt_history()

    if prompt_history.empty:
        st.info("No prompt versions found in grant_prompt_config.")
    else:
        current = prompt_history[prompt_history["is_current"] == True]
        past    = prompt_history[prompt_history["is_current"] == False]

        st.markdown("### Current Prompt")
        if not current.empty:
            row = current.iloc[0]
            active_since = str(row["created_at"])[:10]

            total  = int(row["total_classified"])
            as_q   = int(row["classified_as_question"])
            q_rate = round(as_q / total * 100, 1) if total > 0 else 0
            fp     = int(row["false_positives"])
            cq     = int(row["confirmed_questions"])

            s1, s2, s3, s4, s5 = st.columns(5)
            s1.metric("Version",              f"v{int(row['version'])}")
            s2.metric("Active Since",         active_since)
            s3.metric("Posts Classified",     total)
            s4.metric("Question Rate",        f"{q_rate}%")
            s5.metric("Feedback This Period", f"{fp} FP · {cq} CQ",
                      help="FP = false positives flagged by team · CQ = confirmed questions")

            if row["change_reason"] and str(row["change_reason"]).strip():
                st.info(f"**Last change:** {row['change_reason']}")

            with st.expander("View full prompt text"):
                st.code(row["prompt_text"], language=None)

        st.divider()

        st.markdown("### Prompt History")
        if past.empty:
            st.caption("No previous versions — this is the first prompt.")
        else:
            for _, row in past.iterrows():
                version_label = f"v{int(row['version'])}"
                active_from   = str(row["created_at"])[:10]
                active_to     = str(row["superseded_at"])[:10] if row["superseded_at"] else "—"
                total         = int(row["total_classified"])
                as_q          = int(row["classified_as_question"])
                q_rate        = round(as_q / total * 100, 1) if total > 0 else 0
                fp            = int(row["false_positives"])
                cq            = int(row["confirmed_questions"])

                with st.expander(
                    f"{version_label} · Active {active_from} → {active_to} · "
                    f"{total} classified · {q_rate}% questions · {fp} FP / {cq} CQ"
                ):
                    if row["change_reason"] and str(row["change_reason"]).strip():
                        st.markdown(f"**Why it was replaced:** {row['change_reason']}")
                        st.divider()
                    st.code(row["prompt_text"], language=None)


# ── ADMIN TAB ─────────────────────────────────────────────────────────────────
with tab_admin:
    _admin_api_key = st.secrets.get("mn_admin_api_key", "")

    st.subheader("Grant Coaches")
    st.caption("Coaches listed here appear as assignees in the ticket list. Promoting a member to coach also gives them host role in Mighty Networks so they can generate their own API key.")

    @st.cache_data(ttl=60)
    def load_coaches():
        return bq_client.get_grant_coaches()

    coaches_df = load_coaches()

    if not coaches_df.empty:
        for _, coach in coaches_df.iterrows():
            cc1, cc2, cc3 = st.columns([3, 2, 0.8])
            cc1.markdown(f"**{coach['full_name']}**")
            cc2.caption(coach.get("email") or "")
            if cc3.button("Remove", key=f"remove_coach_{coach['member_id']}"):
                bq_client.remove_grant_coach(int(coach["member_id"]))
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("No grant coaches added yet.")

    st.divider()
    st.markdown("#### Add a Grant Coach")

    @st.cache_data(ttl=30, show_spinner=False)
    def _search(q):
        return bq_client.search_members(q)

    search_query = st.text_input("Search member by name or email", placeholder="e.g. Jane Smith")

    _q = search_query.strip()
    if len(_q) >= 2:
        results = _search(_q)

        if results.empty:
            st.caption("No members found — try a different name or email.")
        else:
            for _, member in results.iterrows():
                m1, m2, m3 = st.columns([3, 2.5, 1.2])
                m1.markdown(f"**{member['full_name']}**")
                m2.caption(member.get("email_address") or "")

                if m3.button("Make Coach", key=f"promote_{member['member_id']}", type="primary"):
                    if not _admin_api_key:
                        st.error("No MN admin API key configured. Add `mn_admin_api_key` to secrets.toml.")
                    else:
                        try:
                            bq_client.mn_promote_to_host(int(member["member_id"]), _admin_api_key)
                            bq_client.add_grant_coach(
                                member_id=int(member["member_id"]),
                                full_name=str(member["full_name"]),
                                email=str(member.get("email_address") or ""),
                                added_by=current_user or "admin",
                            )
                            st.cache_data.clear()
                            st.session_state["invite_name"] = str(member["full_name"])
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")

    if "invite_name" in st.session_state:
        @st.dialog(f"Invite {st.session_state['invite_name']}")
        def _invite_dialog():
            app_url = st.secrets.get("app_url", "https://grant-helpdesk-170880920649.europe-west1.run.app")
            st.markdown("Share this link with the new grant coach:")
            st.code(app_url, language=None)
            st.caption("They can sign in with email/password or Google. On first login they'll be prompted to add their MN API key.")
            if st.button("Done", use_container_width=True):
                del st.session_state["invite_name"]
                st.rerun()
        _invite_dialog()
