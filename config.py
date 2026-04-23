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

TICKET_STATUSES    = ["open", "closed", "cancelled"]
FEEDBACK_STATUSES  = ["not_a_question", "confirmed_question"]
DIFFICULTY_LEVELS  = ["easy", "intermediate", "advanced", "inappropriate"]

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

