"""Fixed identifiers for demo data. Everything here is synthetic."""

from dataclasses import dataclass

DEMO_ORG_ID = "00000000-0000-4000-8000-000000000001"
DEMO_ORG_NAME = "Demo Health Group (synthetic)"
# A second organisation exists only to prove tenant isolation.
OTHER_ORG_ID = "00000000-0000-4000-8000-000000000002"
OTHER_ORG_NAME = "Other Demo Hospital (isolation test)"


@dataclass(frozen=True)
class DemoUser:
    username: str
    display_name: str
    role: str
    org_id: str = DEMO_ORG_ID


DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("dr.khalid", "Dr. Khalid (Physician)", "physician"),
    DemoUser("sara.auth", "Sara (Authorization Officer)", "auth_officer"),
    DemoUser("omar.coder", "Omar (Medical Coder)", "coder"),
    DemoUser("lama.appeals", "Lama (Appeals Officer)", "appeals_officer"),
    DemoUser("faisal.rcm", "Faisal (RCM Manager)", "rcm_manager"),
    DemoUser("noura.audit", "Noura (Auditor)", "auditor"),
)
OTHER_ORG_USER = DemoUser("other.auth", "Other Org Officer", "auth_officer", OTHER_ORG_ID)

DEMO_PAYERS = (
    ("DPA", "Demo Payer A", "جهة دافعة تجريبية أ"),
    ("DPB", "Demo Payer B", "جهة دافعة تجريبية ب"),
    ("DPC", "Demo Payer C", "جهة دافعة تجريبية ج"),
)

# Illustrative single-service price (SAR) used by the demo price list.
MRI_LUMBAR_CODE = "72148"
MRI_LUMBAR_PRICE_SAR = 2800
