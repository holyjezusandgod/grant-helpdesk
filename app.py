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
    padding: 14px;
    min-height: 88px;
}}
.kpi-card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}}
.kpi-icon {{
    width: 32px; height: 32px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.85rem;
    font-weight: 500;
    flex-shrink: 0;
}}
.kpi-label {{
    font-size: 0.68rem;
    color: #6b7280;
    font-weight: 500;
}}
.kpi-value {{
    font-size: 1.6rem;
    font-weight: 500;
    color: #111827;
    line-height: 1;
}}

/* ── KPI Row B plain cards ── */
.kpi-b-card {{
    background: {CARD_BG};
    border-radius: 18px;
    padding: 14px;
    min-height: 80px;
}}
.kpi-b-label {{
    font-size: 0.68rem;
    color: #6b7280;
    font-weight: 500;
    margin-bottom: 6px;
}}
.kpi-b-value {{
    font-size: 1.35rem;
    font-weight: 500;
    color: #111827;
    line-height: 1;
}}

/* ── KPI Goal card ── */
.kpi-goal-card {{
    background: {INDIGO};
    border-radius: 18px;
    padding: 14px;
    min-height: 80px;
}}
.kpi-goal-label {{
    font-size: 0.68rem;
    color: #c4c8e6;
    font-weight: 500;
    margin-bottom: 6px;
}}
.kpi-goal-row {{
    display: flex;
    align-items: baseline;
    gap: 4px;
    margin-bottom: 8px;
}}
.kpi-goal-value {{
    font-size: 1.35rem;
    font-weight: 500;
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
    font-size: 0.68rem;
    font-weight: 500;
    white-space: nowrap;
}}
.badge-open           {{ background: #e1edfb; color: #1d4e8c; }}
.badge-answered       {{ background: #d6f0d6; color: #1f6a1f; }}
.badge-closed         {{ background: #d6f0d6; color: #1f6a1f; }}
.badge-cancelled      {{ background: #fde0e0; color: #8a1f1f; }}
.badge-not_a_question {{ background: #f0f0f0; color: #666;     }}

/* ── Urgency pills (exact mockup colors) ── */
.urg-pill {{ display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 0.68rem; font-weight: 500; white-space: nowrap; }}
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

    # Header
    st.subheader(
        f"{status_icon} {ticket.get('member_name', 'Unknown')}  "
        f"{urgency_icon} {(ticket.get('urgency') or '').capitalize()}  "
        f"· `{content_type}`"
        + (f"  {domain_icon} {ticket.get('domain')}" if domain_icon else "")
    )

    # Metadata
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"**State:** {ticket.get('member_state') or '—'}")
    m2.markdown(f"**City:** {ticket.get('member_city') or '—'}")
    m3.markdown(f"**Member ID:** {ticket.get('member_id') or '—'}")
    m4.markdown(f"**Posted:** {str(ticket.get('created_at', '—'))[:16]}")
    st.markdown(f"[MightyNetworks Profile ↗]({ticket.get('member_permalink', '')})")

    st.divider()

    # Full thread
    thread_id = ticket.get("thread_id") or content_id
    st.markdown("**Thread**")
    with st.spinner("Loading thread…"):
        thread = bq_client.get_thread(thread_id)

    with st.container(height=380):
        for _, item in thread.iterrows():
            is_current = item["content_id"] == content_id
            role = "assistant" if item["author_type"] == "team" else "user"
            indent = "　" * (int(item["depth"]) - 1) if int(item["depth"]) > 1 else ""
            with st.chat_message(role):
                label = f"{indent}**{item['author_name']}** · {str(item['created_at'])[:16]}"
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
            st.rerun()
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
            label_visibility="collapsed", height=120,
        )
        if st.button("Post Answer to MN", key=f"post_answer_{content_id}", type="primary"):
            if answer_body.strip():
                try:
                    bq_client.post_mn_comment(_post_id, answer_body.strip(), _mn_key)
                    st.success("Answer posted to Mighty Networks.")
                    st.cache_data.clear()
                    st.rerun()
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
            "Comment", key=f"comment_{content_id}", label_visibility="collapsed"
        )
        if st.button("Post Comment", key=f"post_comment_{content_id}"):
            if comment_body.strip():
                bq_client.post_comment(content_id, current_user, comment_body.strip())
                st.success("Comment posted.")
                st.rerun()
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

    # ── KPI Row B ─────────────────────────────────────────────────────────────
    answered_today = int(daily_stats.get("answered_today", 0))
    goal           = int(daily_stats.get("goal", config.DAILY_GOAL))
    b1, b2, b3, b4 = st.columns(4)
    b1.markdown(kpi_b_card("In today",        int(daily_stats.get("in_today", 0))),   unsafe_allow_html=True)
    b2.markdown(kpi_b_card("Answered today",  answered_today),                         unsafe_allow_html=True)
    b3.markdown(kpi_b_card("Daily avg (30d)", daily_stats.get("daily_avg", 0)),        unsafe_allow_html=True)
    b4.markdown(goal_card(answered_today, goal),                                       unsafe_allow_html=True)

    # ── Ticket list ───────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-card"><div class="section-card-title">Tickets ({len(tickets)})</div>', unsafe_allow_html=True)

    if tickets.empty:
        st.info("No tickets match the current filters.")
    else:
        # Table header — no separate Grant Coach column; initials avatar IS the dropdown
        h0, h1, h2, h3, h4, h5, h6 = st.columns([0.7, 1.5, 3.5, 1, 1.1, 0.4, 0.35])
        for col, label in zip(
            [h0, h1, h2, h3, h4, h5, h6],
            ["Coach", "Member", "Question", "Urgency", "Status", "Link", ""],
        ):
            col.markdown(f'<span class="tbl-header">{label}</span>', unsafe_allow_html=True)

        for _, row in tickets.iterrows():
            c0, c1, c2, c3, c4, c5, c6 = st.columns([0.7, 1.5, 3.5, 1, 1.1, 0.4, 0.35])

            # Grant Coach initials — plain text
            _current_assignee = row.get("assigned_to") or ""
            _initials_display = _initials(_current_assignee) if _current_assignee else "·"
            c0.markdown(f'<div style="text-align:center;font-size:0.85rem;font-weight:600;color:#4a52a3;padding-top:6px">{_initials_display}</div>', unsafe_allow_html=True)

            # Member name button + timestamp
            mem_name = row["member_name"] or "Unknown"
            if c1.button(
                mem_name,
                key=f"member_{row['content_id']}",
                use_container_width=True,
            ):
                st.session_state.member_id_filter = str(row["member_id"])
                st.rerun()
            c1.caption(str(row["created_at"])[:10])

            # Domain icon + question preview
            domain_icon = DOMAIN_ICON.get(row.get("domain") or "", "")
            preview_text = str(row["body_preview"] or "")[:110]
            if domain_icon:
                c2.markdown(
                    f'<span class="domain-circle">{domain_icon}</span> <small>{preview_text}</small>',
                    unsafe_allow_html=True,
                )
            else:
                c2.caption(preview_text)

            # Urgency pill
            urg = (row.get("urgency") or "").lower()
            c3.markdown(
                f'<span class="urg-pill urg-{urg}">{urg.capitalize() or "—"}</span>',
                unsafe_allow_html=True,
            )

            # Status badge
            status = (row.get("ticket_status") or "").lower()
            c4.markdown(
                f'<span class="badge badge-{status}">{status.replace("_", " ").capitalize()}</span>',
                unsafe_allow_html=True,
            )

            # Permalink
            permalink = row.get("permalink") or ""
            if permalink:
                c5.markdown(f"[↗]({permalink})")

            # Open ticket button
            if c6.button("→", key=f"open_{row['content_id']}"):
                show_ticket_dialog(row["content_id"])

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
