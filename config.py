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

TICKET_STATUSES    = ["new", "assigned", "closed", "cancelled"]
DIFFICULTY_LEVELS  = ["easy", "intermediate", "advanced", "inappropriate"]

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

