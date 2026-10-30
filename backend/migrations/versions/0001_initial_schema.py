"""Initial schema: tenancy, clinical record, policies, authorization lifecycle, audit (PRD §10).

Revision ID: 0001
Revises:
Create Date: 2026-10-30
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CASE_STATES = (
    "DRAFT", "RISK_DETECTED", "EVIDENCE_SEARCHING", "DECISION_READY", "SUBMITTED",
    "APPROVED", "DENIED", "RECOVERY_IN_PROGRESS", "APPEAL_READY", "RECOVERED",
)
_states_sql = ", ".join(f"'{s}'" for s in CASE_STATES)

# Tables that hold tenant data. Each gets organization_id + an RLS policy.
TENANT_TABLES = [
    "facilities", "users", "user_roles", "patients", "encounters", "clinical_documents",
    "clinical_facts", "evidence_spans", "payers", "payer_policies", "policy_versions",
    "policy_rules", "policy_chunks", "price_lists", "authorization_requests",
    "authorization_requirements", "authorization_evidence", "authorization_events",
    "readiness_scores", "revenue_risk", "claims", "denials", "denial_reasons", "appeals",
    "appeal_evidence", "recovery_cases", "deadlines", "agent_runs", "human_reviews",
    "audit_logs", "nphies_transactions",
]

ORG = "organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE"
STAMPS = "created_at timestamptz NOT NULL DEFAULT now()"

DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mujeaz_app') THEN
    CREATE ROLE mujeaz_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
END $$;

-- ---------------------------------------------------------------- tenancy & identity
CREATE TABLE organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  {STAMPS}
);

CREATE TABLE roles (
  name text PRIMARY KEY,
  description text NOT NULL
);

CREATE TABLE facilities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  code text NOT NULL,
  name text NOT NULL,
  name_ar text,
  {STAMPS},
  UNIQUE (organization_id, code)
);

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  username text NOT NULL UNIQUE,
  display_name text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  {STAMPS}
);

CREATE TABLE user_roles (
  {ORG},
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_name text NOT NULL REFERENCES roles(name),
  PRIMARY KEY (user_id, role_name)
);

-- ---------------------------------------------------------------- clinical record
CREATE TABLE patients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  external_ref text NOT NULL,
  display_name text NOT NULL,
  birth_year int,
  gender text CHECK (gender IN ('M','F','U')),
  {STAMPS},
  UNIQUE (organization_id, external_ref)
);

CREATE TABLE encounters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  patient_id uuid NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  facility_id uuid REFERENCES facilities(id),
  encounter_ref text NOT NULL,
  kind text NOT NULL,
  started_on date NOT NULL,
  summary text,
  {STAMPS},
  UNIQUE (organization_id, encounter_ref)
);

CREATE TABLE clinical_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  patient_id uuid NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  encounter_id uuid REFERENCES encounters(id) ON DELETE SET NULL,
  doc_ref text NOT NULL,
  doc_type text NOT NULL,
  language text NOT NULL CHECK (language IN ('en','ar','mixed')),
  authored_on date NOT NULL,
  content text NOT NULL,
  content_sha256 char(64) NOT NULL,
  {STAMPS},
  UNIQUE (organization_id, doc_ref)
);

CREATE TABLE evidence_spans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  document_id uuid NOT NULL REFERENCES clinical_documents(id) ON DELETE CASCADE,
  char_start int NOT NULL CHECK (char_start >= 0),
  char_end int NOT NULL,
  quoted text NOT NULL,
  {STAMPS},
  CHECK (char_end > char_start)
);

-- ---------------------------------------------------------------- payers & policy
CREATE TABLE payers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  code text NOT NULL,
  name text NOT NULL,
  name_ar text,
  is_demo boolean NOT NULL DEFAULT true,
  {STAMPS},
  UNIQUE (organization_id, code)
);

CREATE TABLE payer_policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  payer_id uuid NOT NULL REFERENCES payers(id) ON DELETE CASCADE,
  code text NOT NULL,
  title text NOT NULL,
  title_ar text,
  {STAMPS},
  UNIQUE (organization_id, code)
);

CREATE TABLE policy_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  policy_id uuid NOT NULL REFERENCES payer_policies(id) ON DELETE CASCADE,
  version text NOT NULL,
  effective_from date NOT NULL,
  source_text text NOT NULL,
  source_sha256 char(64) NOT NULL,
  {STAMPS},
  UNIQUE (policy_id, version)
);

CREATE TABLE policy_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  policy_version_id uuid NOT NULL REFERENCES policy_versions(id) ON DELETE CASCADE,
  code text NOT NULL,
  title text NOT NULL,
  title_ar text,
  requirement text NOT NULL,
  requirement_ar text,
  mandatory boolean NOT NULL DEFAULT true,
  spec jsonb NOT NULL DEFAULT '{{}}'::jsonb,
  {STAMPS},
  UNIQUE (policy_version_id, code)
);

CREATE TABLE policy_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  policy_version_id uuid NOT NULL REFERENCES policy_versions(id) ON DELETE CASCADE,
  ord int NOT NULL,
  content text NOT NULL,
  embedding vector(768),
  {STAMPS},
  UNIQUE (policy_version_id, ord)
);

CREATE TABLE price_lists (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  payer_id uuid REFERENCES payers(id) ON DELETE CASCADE,
  service_code text NOT NULL,
  description text NOT NULL,
  price_sar numeric(12,2) NOT NULL CHECK (price_sar >= 0),
  is_demo boolean NOT NULL DEFAULT true,
  {STAMPS}
);

-- ---------------------------------------------------------------- authorization lifecycle
CREATE TABLE authorization_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  case_number text NOT NULL,
  legacy_id text,
  patient_id uuid NOT NULL REFERENCES patients(id),
  facility_id uuid REFERENCES facilities(id),
  payer_id uuid NOT NULL REFERENCES payers(id),
  physician_name text NOT NULL,
  specialty text NOT NULL,
  requested_service text NOT NULL,
  requested_service_ar text,
  service_code text NOT NULL,
  diagnosis_code text NOT NULL,
  diagnosis_display text,
  financial_value_sar numeric(12,2) NOT NULL CHECK (financial_value_sar >= 0),
  status text NOT NULL CHECK (status IN ({_states_sql})),
  clinical_note text NOT NULL,
  data_source text NOT NULL CHECK (data_source IN ('legacy-demo','synthetic')),
  extra jsonb NOT NULL DEFAULT '{{}}'::jsonb,
  requested_on date NOT NULL,
  {STAMPS},
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, case_number)
);

CREATE TABLE clinical_facts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  document_id uuid REFERENCES clinical_documents(id) ON DELETE SET NULL,
  category text NOT NULL,
  fact text NOT NULL,
  fact_ar text,
  source_label text NOT NULL,
  char_start int,
  char_end int,
  fact_date date,
  confidence int NOT NULL CHECK (confidence BETWEEN 0 AND 100),
  ord int NOT NULL DEFAULT 0,
  {STAMPS}
);

CREATE TABLE authorization_requirements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  policy_rule_id uuid REFERENCES policy_rules(id),
  code text NOT NULL,
  title text NOT NULL,
  title_ar text,
  requirement text NOT NULL,
  requirement_ar text,
  status text NOT NULL CHECK (status IN ('PASSED','WARNING','FAILED','PENDING')),
  evidence_source text,
  ord int NOT NULL DEFAULT 0,
  {STAMPS}
);

CREATE TABLE authorization_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  requirement text NOT NULL,
  requirement_ar text,
  status text NOT NULL CHECK (status IN ('FOUND','PARTIAL','MISSING')),
  matched_fact text,
  source_label text,
  evidence_date date,
  confidence int NOT NULL CHECK (confidence BETWEEN 0 AND 100),
  evidence_span_id uuid REFERENCES evidence_spans(id) ON DELETE SET NULL,
  ord int NOT NULL DEFAULT 0,
  {STAMPS}
);

CREATE TABLE authorization_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  from_status text,
  to_status text NOT NULL,
  actor text NOT NULL,
  note text
);

CREATE TABLE readiness_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  computed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  clinical_evidence int NOT NULL,
  policy_match int NOT NULL,
  documentation int NOT NULL,
  coding_integrity int NOT NULL,
  required_attachments int NOT NULL,
  administrative_completeness int NOT NULL,
  overall_score int NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
  label text NOT NULL,
  label_ar text NOT NULL,
  gate_applied text,
  warning text,
  warning_ar text,
  method text NOT NULL
);

CREATE TABLE revenue_risk (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  computed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  financial_value_sar numeric(12,2) NOT NULL,
  denial_risk_pct int NOT NULL CHECK (denial_risk_pct BETWEEN 0 AND 100),
  revenue_at_risk_sar numeric(12,2) NOT NULL,
  recoverable_value_sar numeric(12,2) NOT NULL,
  priority text NOT NULL CHECK (priority IN ('HIGH','MEDIUM','LOW'))
);

CREATE TABLE claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  claim_number text NOT NULL,
  total_sar numeric(12,2) NOT NULL,
  status text NOT NULL,
  {STAMPS}
);

CREATE TABLE denial_reasons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  code text NOT NULL,
  display text NOT NULL,
  category text NOT NULL,
  is_demo boolean NOT NULL DEFAULT true,
  UNIQUE (organization_id, code)
);

CREATE TABLE denials (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  claim_id uuid REFERENCES claims(id),
  reason_code text NOT NULL,
  reason text NOT NULL,
  reason_ar text,
  root_cause text,
  root_cause_ar text,
  missing_requirement text,
  missing_requirement_ar text,
  denied_at timestamptz NOT NULL DEFAULT now(),
  simulated boolean NOT NULL DEFAULT true
);

CREATE TABLE appeals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  denial_id uuid REFERENCES denials(id),
  status text NOT NULL,
  strategy text,
  strategy_ar text,
  letter_en text,
  letter_ar text,
  strength int CHECK (strength BETWEEN 0 AND 100),
  approved_by uuid REFERENCES users(id),
  {STAMPS}
);

CREATE TABLE appeal_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  appeal_id uuid NOT NULL REFERENCES appeals(id) ON DELETE CASCADE,
  fact text NOT NULL,
  fact_ar text,
  source_label text NOT NULL,
  evidence_date date,
  ord int NOT NULL DEFAULT 0
);

CREATE TABLE recovery_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  denial_id uuid REFERENCES denials(id),
  status text NOT NULL,
  recoverable_value_sar numeric(12,2) NOT NULL DEFAULT 0,
  opened_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE deadlines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  kind text NOT NULL,
  due_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'OPEN',
  is_demo boolean NOT NULL DEFAULT true
);

-- ---------------------------------------------------------------- agents & reviews
CREATE TABLE prompts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  version text NOT NULL,
  body_sha256 char(64) NOT NULL,
  body text NOT NULL,
  {STAMPS},
  UNIQUE (name, version)
);

CREATE TABLE agent_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid REFERENCES authorization_requests(id) ON DELETE CASCADE,
  agent_id text NOT NULL CHECK (agent_id IN ('A1','A2','A3','A4','A5','A6')),
  name text NOT NULL,
  name_ar text,
  status text NOT NULL CHECK (status IN ('IDLE','RUNNING','COMPLETED','FLAGGED','FAILED')),
  output_summary text,
  output_summary_ar text,
  model text,
  prompt_version text,
  inputs_sha256 char(64),
  output jsonb,
  latency_ms int,
  tokens_in int,
  tokens_out int,
  cost_usd numeric(10,6),
  started_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE human_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  reviewer_user_id uuid NOT NULL REFERENCES users(id),
  gate text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
  note text,
  reviewed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE nphies_transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  direction text NOT NULL CHECK (direction IN ('OUTBOUND','INBOUND')),
  resource_type text NOT NULL,
  simulated boolean NOT NULL DEFAULT true,
  validated boolean NOT NULL DEFAULT false,
  payload jsonb NOT NULL,
  {STAMPS}
);

-- ---------------------------------------------------------------- audit (ADR 0004)
CREATE TABLE audit_logs (
  id bigserial PRIMARY KEY,
  {ORG},
  chain_key text NOT NULL,
  seq int NOT NULL CHECK (seq >= 1),
  occurred_at timestamptz NOT NULL,
  actor_id text NOT NULL,
  actor_role text NOT NULL,
  action text NOT NULL,
  details jsonb NOT NULL DEFAULT '{{}}'::jsonb,
  prev_hash char(64) NOT NULL,
  hash char(64) NOT NULL,
  UNIQUE (chain_key, seq)
);

CREATE FUNCTION audit_logs_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_logs is append-only: % is not allowed', TG_OP;
END $$;

CREATE TRIGGER audit_logs_no_update BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable();
CREATE TRIGGER audit_logs_no_truncate BEFORE TRUNCATE ON audit_logs
  FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_immutable();

-- ---------------------------------------------------------------- indexes
CREATE INDEX ix_auth_req_org_status ON authorization_requests (organization_id, status);
CREATE INDEX ix_docs_patient ON clinical_documents (patient_id, authored_on);
CREATE INDEX ix_facts_req ON clinical_facts (authorization_request_id);
CREATE INDEX ix_reqs_req ON authorization_requirements (authorization_request_id);
CREATE INDEX ix_evidence_req ON authorization_evidence (authorization_request_id);
CREATE INDEX ix_events_req ON authorization_events (authorization_request_id, occurred_at);
CREATE INDEX ix_scores_req ON readiness_scores (authorization_request_id, computed_at DESC);
CREATE INDEX ix_risk_req ON revenue_risk (authorization_request_id, computed_at DESC);
CREATE INDEX ix_runs_req ON agent_runs (authorization_request_id, agent_id, started_at DESC);
CREATE INDEX ix_audit_chain ON audit_logs (chain_key, seq);

-- ---------------------------------------------------------------- login lookup
-- Login happens before an organisation is known, so RLS would hide the user.
-- This narrow SECURITY DEFINER function returns only what token issuance needs.
CREATE FUNCTION auth_lookup_user(p_username text)
RETURNS TABLE (user_id uuid, organization_id uuid, display_name text, roles text[])
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT u.id, u.organization_id, u.display_name,
         coalesce(array_agg(ur.role_name ORDER BY ur.role_name) FILTER (WHERE ur.role_name IS NOT NULL), '{{}}')
  FROM users u LEFT JOIN user_roles ur ON ur.user_id = u.id
  WHERE u.username = p_username AND u.active
  GROUP BY u.id;
$$;
REVOKE ALL ON FUNCTION auth_lookup_user(text) FROM PUBLIC;
"""


def _sql(statement: str) -> None:
    # Send the DDL on the raw psycopg cursor with no parameters: psycopg then uses the
    # simple query protocol, which allows several statements and leaves '%' untouched.
    # Runs inside Alembic's transaction on the same connection.
    dbapi_conn = op.get_bind().connection.dbapi_connection
    assert dbapi_conn is not None
    with dbapi_conn.cursor() as cur:
        cur.execute(statement)


def upgrade() -> None:
    _sql(DDL)
    for table in TENANT_TABLES:
        _sql(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        _sql(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (organization_id = nullif(current_setting('app.org_id', true), '')::uuid) "
            "WITH CHECK (organization_id = nullif(current_setting('app.org_id', true), '')::uuid)"
        )
    _sql(
        """
        GRANT USAGE ON SCHEMA public TO mujeaz_app;
        GRANT SELECT ON organizations, roles, prompts TO mujeaz_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO mujeaz_app;
        REVOKE UPDATE, DELETE, TRUNCATE ON audit_logs FROM mujeaz_app;
        REVOKE INSERT, UPDATE, DELETE ON organizations, roles, prompts FROM mujeaz_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mujeaz_app;
        GRANT EXECUTE ON FUNCTION auth_lookup_user(text) TO mujeaz_app;
        """
    )


def downgrade() -> None:
    _sql("DROP FUNCTION IF EXISTS auth_lookup_user(text)")
    tables = [
        "audit_logs", "nphies_transactions", "human_reviews", "agent_runs", "prompts", "deadlines",
        "recovery_cases", "appeal_evidence", "appeals", "denials", "denial_reasons", "claims",
        "revenue_risk", "readiness_scores", "authorization_events", "authorization_evidence",
        "authorization_requirements", "clinical_facts", "authorization_requests", "price_lists",
        "policy_chunks", "policy_rules", "policy_versions", "payer_policies", "payers",
        "evidence_spans", "clinical_documents", "encounters", "patients", "user_roles", "users",
        "facilities", "roles", "organizations",
    ]
    for table in tables:
        _sql(f"DROP TABLE IF EXISTS {table} CASCADE")
    _sql("DROP FUNCTION IF EXISTS audit_logs_immutable()")
    _sql("REVOKE ALL ON SCHEMA public FROM mujeaz_app")
