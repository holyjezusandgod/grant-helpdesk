PROJECT_ID = "bigtribebuilders"
DATASET    = "grant_helpdesk"

TICKETS_TABLE  = f"{PROJECT_ID}.{DATASET}.grant_tickets"
META_TABLE     = f"{PROJECT_ID}.{DATASET}.ticket_metadata"
COMMENTS_TABLE = f"{PROJECT_ID}.{DATASET}.ticket_comments"
COMMENTS_VIEW  = f"{PROJECT_ID}.{DATASET}.grant_comments"
TEAM_TABLE     = f"{PROJECT_ID}.{DATASET}.stg_grant_team"

APP_NAME     = "Lesko Help Desk"
APP_VERSION  = "0.1"
DAILY_GOAL   = 50

# A ticket's lifecycle is binary: open (live) vs terminal (resolved).
# "assigned" is NOT a status — assignment is orthogonal metadata in assigned_to.
TICKET_STATUSES    = ["open", "answered", "closed", "cancelled", "flagged"]
FEEDBACK_STATUSES  = ["not_a_question", "confirmed_question"]

# Terminal = the ticket has reached a resolved/closed end-state. Everything else
# (open, answered, flagged, NULL) is "open"/live. Single source of truth shared by
# the Open KPI and the default ticket list so the two can never diverge.
TERMINAL_STATUSES  = ["closed", "cancelled", "not_a_question", "confirmed_question"]


def is_open_status(status) -> bool:
    """True when a ticket is live (not terminal). NULL/empty defaults to open."""
    return (status or "open") not in TERMINAL_STATUSES

MEMBER_ASSIGNMENTS_TABLE = f"{PROJECT_ID}.{DATASET}.member_assignment_overrides"
LOGS_TABLE               = f"{PROJECT_ID}.{DATASET}.app_logs"

# Dataform repository — used to trigger table refreshes after assignments change.
# DATAFORM_REGION: the GCP region your Dataform repo lives in (e.g. "europe-west4").
# DATAFORM_REPOSITORY: the repository name as it appears in the Dataform UI.
DATAFORM_REGION     = "europe-west1"
DATAFORM_REPOSITORY = "grant-helpdesk"

PROMPT_CONFIG_TABLE     = f"{PROJECT_ID}.{DATASET}.grant_prompt_config"
FEEDBACK_VIEW           = f"{PROJECT_ID}.{DATASET}.grant_classification_feedback"
CLASSIFIER_TABLE        = f"{PROJECT_ID}.{DATASET}.grant_question_classifier"

TEAM_API_KEYS_TABLE     = f"{PROJECT_ID}.{DATASET}.team_api_keys"
GRANT_COACHES_TABLE     = f"{PROJECT_ID}.{DATASET}.grant_coaches"
FOLLOWUP_QUEUE_TABLE    = f"{PROJECT_ID}.{DATASET}.followup_queue"
STANDARD_REPLIES_TABLE  = f"{PROJECT_ID}.{DATASET}.standard_replies"

# space_id → space_name lookup. Populated monthly by jobs/sync_spaces.py from
# the MN Admin API (/spaces). Read once (cached) to label which space/channel a
# ticket was commented in. Comments on a member's own profile carry space_id =
# MN_NETWORK_ID → rendered as "Member bio" (see mn_format.space_label).
SPACE_NAMES_TABLE       = f"{PROJECT_ID}.{DATASET}.space_names"

MN_NETWORK_ID  = "4022250"
MN_API_BASE    = "https://api.mn.co/admin/v1"

# Colleagues a coach can @mention from the answer pop-up. The display name is
# what MN renders in the mention (MN does not look it up by id), so keep it the
# person's real name. member_id is their Mighty Networks member id.
TAG_COLLEAGUES = [
    {"name": "Roger White",       "member_id": 20608038},
    {"name": "Amber Littlefield", "member_id": 18218501},
    {"name": "Amber Hawkins",     "member_id": 10443685},
    {"name": "Megan P",           "member_id": 11554451},
]

DOMAINS = [
    "Pay Debt & Bills",
    "Home & Housing Help",
    "Cars & Car Repairs",
    "Healthcare Assistance",
    "Start A Business",
    "Launch A Nonprofit",
    "Boost Your Career",
    "Taxes Help Guidance",
    "Find Legal Help",
    "Family & Children",
    "Seniors & Disabilities",
    "Programs for Veterans",
    "Community Support",
    "Other",
]

