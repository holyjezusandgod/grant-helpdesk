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
PURPLE  = "#7040a8"
PINK    = "#e040a0"
CYAN    = "#35c0e0"

st.markdown(f"""
<style>
/* ── Global white background ── */
.stApp {{
    background-color: #ffffff !important;
}}
section[data-testid="stMain"] > div {{
    background-color: #ffffff !important;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: #1e2a5e !important;
}}
[data-testid="stSidebar"] * {{
    color: #ffffff !important;
}}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stRadio label {{
    color: #a0b4d8 !important;
    font-size: 0.78rem !important;
}}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
    color: #ffffff !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.15) !important;
}}

/* ── Buttons ── */
button[data-testid="baseButton-secondary"] {{
    background-color: {INDIGO} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
}}
button[data-testid="baseButton-secondary"]:hover {{
    background-color: #3a4190 !important;
    color: #ffffff !important;
}}
button[data-testid="baseButton-primary"] {{
    background-color: {INDIGO} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
}}

/* ── Status badges ── */
.badge {{
    display: inline-block;
    padding: 2px 9px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}}
.badge-open           {{ background: {BLUE};   color: #fff; }}
.badge-answered       {{ background: {GREEN};  color: #fff; }}
.badge-closed         {{ background: {GREEN};  color: #fff; }}
.badge-cancelled      {{ background: {RED};    color: #fff; }}
.badge-not_a_question {{ background: #aaa;     color: #fff; }}

/* ── Urgency text ── */
.urg-normal   {{ color: {GREEN};  font-weight: 600; font-size: 0.82rem; }}
.urg-urgent   {{ color: #c49a00; font-weight: 600; font-size: 0.82rem; }}
.urg-critical {{ color: {RED};    font-weight: 600; font-size: 0.82rem; }}

/* ── Metric cards ── */
[data-testid="metric-container"] {{
    background: #f4f6fb;
    border-left: 4px solid {INDIGO};
    border-radius: 8px;
    padding: 10px 14px !important;
}}
[data-testid="metric-container"] label {{
    color: #555 !important;
    font-size: 0.8rem !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {INDIGO} !important;
    font-weight: 700;
}}

/* ── Tabs ── */
button[data-baseweb="tab"] {{
    font-weight: 600;
    color: #555 !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {INDIGO} !important;
    border-bottom: 3px solid {INDIGO} !important;
}}

/* ── Page header banner ── */
.lesko-header {{
    background: linear-gradient(135deg, {INDIGO} 0%, {BLUE} 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 10px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.lesko-header h2 {{
    margin: 0;
    font-size: 1.2rem;
    color: white !important;
}}
.lesko-header .sub {{
    font-size: 0.82rem;
    opacity: 0.85;
    margin-top: 2px;
}}

/* ── Dividers ── */
hr {{
    border-color: #e8eaf0 !important;
}}
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

# ── Auth ───────────────────────────────────────────────────────────────────────
if not st.user.is_logged_in:
    # ── Login page ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        display:flex; flex-direction:column; align-items:center;
        justify-content:center; min-height:70vh; gap:12px;
    ">
      <div style="
          background:linear-gradient(135deg,{INDIGO} 0%,{BLUE} 100%);
          color:white; border-radius:16px; padding:40px 56px;
          text-align:center; max-width:420px; box-shadow:0 4px 24px rgba(74,82,163,0.18);
      ">
        <div style="font-size:3rem; margin-bottom:8px;">🎯</div>
        <h2 style="margin:0 0 6px; color:white; font-size:1.6rem;">Lesko Help Desk</h2>
        <p style="opacity:0.85; font-size:0.9rem; margin:0 0 28px;">
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
    st.stop()

user         = st.user
current_user = user.email or user.name or ""

# ── Session state defaults ─────────────────────────────────────────────────────
if "member_id_filter" not in st.session_state:
    st.session_state.member_id_filter = ""

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    # User account block
    avatar_url = getattr(user, "picture", None)
    name       = getattr(user, "name",    None) or current_user
    email      = getattr(user, "email",   None) or ""

    if avatar_url:
        ac1, ac2 = st.columns([1, 3])
        ac1.image(avatar_url, width=40)
        ac2.markdown(f"**{name}**")
        ac2.caption(email)
    else:
        st.markdown(f"**{name}**")
        st.caption(email)

    if st.button("Sign out", use_container_width=True):
        st.logout()

    st.divider()
    st.markdown("### 🎯 Lesko Help Desk")

    st.divider()
    st.subheader("Filters")

    today = datetime.date.today()

    def filter_row(label):
        a, b = st.columns([1, 2])
        a.markdown(f"**{label}**")
        return b

    # 1. Status (feedback statuses live in the Train AI tab, not here)
    _status_opts = ["All"] + config.TICKET_STATUSES
    filter_status = filter_row("Status").selectbox(
        "Status", _status_opts,
        index=_status_opts.index("open"),
        format_func=lambda s: s if s == "All" else s.replace("_", " ").title(),
        label_visibility="collapsed",
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
    filter_assignee = filter_row("Assigned To").selectbox(
        "Assigned To", ["All"] + team_members,
        label_visibility="collapsed",
    )

    # 4. Member ID
    filter_member_id = filter_row("Member ID").text_input(
        "Member ID", value=st.session_state.member_id_filter,
        label_visibility="collapsed",
    )

    # 5. Urgency
    filter_urgency = filter_row("Urgency").selectbox(
        "Urgency", ["All", "Normal", "Urgent", "Critical"],
        label_visibility="collapsed",
    )

    # 6. Domain
    filter_domain = filter_row("Domain").selectbox(
        "Domain", ["All"] + config.DOMAINS,
        label_visibility="collapsed",
    )

    if st.button("🔄 Refresh", use_container_width=True):
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
        assignee_options    = ["— unassigned —"] + team_members
        current_assignee    = ticket.get("assigned_to") or "— unassigned —"
        if current_assignee not in assignee_options:
            current_assignee = "— unassigned —"
        new_assignee = st.selectbox(
            "Assigned To",
            assignee_options,
            index=assignee_options.index(current_assignee),
            key=f"assignee_{content_id}",
        )

    # Override checkbox — only shown when an assignee is selected
    override_assignment = False
    if new_assignee != "— unassigned —" and can_edit:
        override_assignment = st.checkbox(
            f"Set as permanent helper for **{ticket.get('member_name', 'this member')}**",
            value=False,
            help="Overrides the automatic assignment rule — all future tickets from this member will go to this helper.",
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
        domain_options  = ["— unset —"] + config.DOMAINS
        current_domain  = ticket.get("domain") or "— unset —"
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
            st.success("Saved." if not override_assignment else "Saved — permanent helper updated.")
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
        # Extract numeric post ID from content_id (e.g. "post_12345" → "12345")
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

    # Call sheet stub
    with st.expander("📋 Call Sheet Report"):
        st.caption("Prompt template wiring coming soon.")
        st.text_input("State",  value=ticket.get("member_state") or "", disabled=True)
        st.text_input("Domain", value=ticket.get("domain") or "",       disabled=True)
        st.button("Generate Report", disabled=True, help="Coming soon", key=f"callsheet_{content_id}")

    # Member history
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
# TABS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="lesko-header">
  <span style="font-size:1.8rem">🎯</span>
  <div>
    <h2>Lesko Help Desk</h2>
    <div class="sub">Grant support queue — powered by Lesko community data</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab_main, tab_reports, tab_train, tab_settings = st.tabs(["🎫 Tickets", "📊 Reports", "🤖 Train AI", "⚙️ Settings"])


# ── MAIN TAB ──────────────────────────────────────────────────────────────────
with tab_main:
    tickets     = load_tickets(
        filter_status, date_from, date_to,
        filter_assignee, filter_member_id,
        filter_urgency, filter_domain,
    )
    open_stats  = load_open_stats()
    daily_stats = load_daily_stats()

    # KPI Row A — open breakdown
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("🔵 Open",     int(open_stats.get("open",     0)))
    a2.metric("🟢 Normal",   int(open_stats.get("normal",   0)))
    a3.metric("🟡 Urgent",   int(open_stats.get("urgent",   0)))
    a4.metric("🔴 Critical", int(open_stats.get("critical", 0)))

    # KPI Row B — daily productivity
    answered_today = int(daily_stats.get("answered_today", 0))
    goal           = int(daily_stats.get("goal", config.DAILY_GOAL))
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("📥 In today",       int(daily_stats.get("in_today",   0)))
    b2.metric("✅ Answered today",  answered_today)
    b3.metric("📈 Daily avg (30d)", daily_stats.get("daily_avg",     0))
    b4.metric("🎯 Goal progress",  f"{answered_today} / {goal}")

    st.divider()

    # Ticket table
    st.subheader(f"Tickets ({len(tickets)})")

    if tickets.empty:
        st.info("No tickets match the current filters.")
    else:
        # Table header
        h0, h1, h2, h3, h4, h5, h6, h7 = st.columns([1.4, 1.5, 3, 1.5, 1.1, 1.2, 0.5, 0.4])
        for col, label in zip(
            [h0, h1, h2, h3, h4, h5, h6, h7],
            ["Timestamp", "Member", "Question", "Assigned To", "Urgency", "Status", "Link", ""],
        ):
            col.markdown(f"**{label}**")

        st.divider()

        def _save_quick_assignee(content_id):
            new_val = st.session_state[f"quick_assignee_{content_id}"]
            assignee_val = "" if new_val == "— unassigned —" else new_val
            bq_client.set_ticket_assignee(content_id, assignee_val)
            st.cache_data.clear()

        for _, row in tickets.iterrows():
            c0, c1, c2, c3, c4, c5, c6, c7 = st.columns([1.4, 1.5, 3, 1.5, 1.1, 1.2, 0.5, 0.4])

            c0.caption(str(row["created_at"])[:16])

            # Member name — clicking fills the member ID filter
            if c1.button(
                row["member_name"] or "Unknown",
                key=f"member_{row['content_id']}",
                use_container_width=True,
            ):
                st.session_state.member_id_filter = str(row["member_id"])
                st.rerun()

            domain_icon = DOMAIN_ICON.get(row.get("domain") or "", "")
            preview_text = str(row["body_preview"] or "")[:120]
            c2.caption(f"{domain_icon} {preview_text}" if domain_icon else preview_text)

            # Assignee dropdown — saves on change without opening the ticket dialog
            _assignee_opts = ["— unassigned —"] + team_members
            _current_assignee = row.get("assigned_to") or "— unassigned —"
            if _current_assignee not in _assignee_opts:
                _current_assignee = "— unassigned —"
            c3.selectbox(
                "Assigned To",
                _assignee_opts,
                index=_assignee_opts.index(_current_assignee),
                key=f"quick_assignee_{row['content_id']}",
                label_visibility="collapsed",
                on_change=_save_quick_assignee,
                args=(row["content_id"],),
            )
            urg = (row.get("urgency") or "").lower()
            urg_css = {"normal": "urg-normal", "urgent": "urg-urgent", "critical": "urg-critical"}.get(urg, "")
            c4.markdown(f'<span class="{urg_css}">{URGENCY_ICON.get(urg, "⚪")} {urg.capitalize()}</span>', unsafe_allow_html=True)

            status = (row.get("ticket_status") or "").lower()
            c5.markdown(f'<span class="badge badge-{status}">{STATUS_ICON.get(status, "⚪")} {status.replace("_", " ").capitalize()}</span>', unsafe_allow_html=True)

            permalink = row.get("permalink") or ""
            if permalink:
                c6.markdown(f"[🔗]({permalink})")

            if c7.button("→", key=f"open_{row['content_id']}"):
                show_ticket_dialog(row["content_id"])


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

    # 12.1 Volume
    st.markdown("#### Volume — Tickets In vs Answered")
    vol = load_report("volume", str(r_date_from), str(r_date_to))
    if not vol.empty:
        st.bar_chart(vol.set_index("date")[["tickets_in", "tickets_closed"]])
    else:
        st.caption("No data for this period.")

    st.divider()

    # 12.2 Response time
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

    # 12.3 Team productivity
    st.markdown("#### Team Productivity — Tickets Closed")
    tp = load_report("team_productivity", str(r_date_from), str(r_date_to))
    if not tp.empty:
        st.bar_chart(tp.set_index("assigned_to")["tickets_closed"])
    else:
        st.caption("No data for this period.")

    st.divider()

    # 12.4 Domain breakdown
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

    # Load queue into session state once; a manual reload clears it
    if "train_queue" not in st.session_state:
        with st.spinner("Loading review queue…"):
            q_df = bq_client.get_unreviewed_rejects()
            st.session_state.train_queue = q_df.to_dict("records")
            st.session_state.train_idx   = 0

    queue   = st.session_state.train_queue
    idx     = st.session_state.train_idx
    total   = len(queue)
    remaining = total - idx

    if remaining <= 0:
        st.success("All caught up — nothing left to review!")
        if st.button("Reload queue"):
            del st.session_state["train_queue"]
            st.rerun()
    else:
        # Progress bar
        st.progress(idx / total if total > 0 else 1.0)
        st.caption(f"{idx} reviewed · {remaining} remaining")
        st.divider()

        item = queue[idx]

        # ── Engagement card ───────────────────────────────────────────────────
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

        # ── Decision buttons ──────────────────────────────────────────────────
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
    # ── Mighty Networks API Key ───────────────────────────────────────────────
    st.subheader("Your Mighty Networks API Key")
    st.caption(
        "Required to post answers directly to Mighty Networks from the ticket dialog. "
        "Each team member needs their own key. Generate one in your MN admin panel under "
        "**Admin → Settings → API Keys**."
    )
    _saved_key = bq_client.get_mn_api_key(current_user) if current_user else None
    _key_input = st.text_input(
        "API Key",
        value=_saved_key or "",
        type="password",
        placeholder="Paste your Mighty Networks API key here",
    )
    if st.button("Save API Key", type="primary"):
        if _key_input.strip():
            bq_client.save_mn_api_key(current_user, _key_input.strip())
            st.success("API key saved.")
        else:
            st.warning("Please enter an API key.")

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

        # ── Current prompt ────────────────────────────────────────────────────
        st.markdown("### Current Prompt")
        if not current.empty:
            row = current.iloc[0]
            active_since = str(row["created_at"])[:10]

            total   = int(row["total_classified"])
            as_q    = int(row["classified_as_question"])
            q_rate  = round(as_q / total * 100, 1) if total > 0 else 0
            fp      = int(row["false_positives"])
            cq      = int(row["confirmed_questions"])

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

        # ── Prompt history ────────────────────────────────────────────────────
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
