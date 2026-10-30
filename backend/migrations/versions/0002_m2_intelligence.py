"""M2 intelligence: document chunks (Arabic + English full-text), analysis runs, fact/evidence provenance.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ORG = "organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE"
NEW_TABLES = ["document_chunks", "analysis_runs"]

DDL = f"""
CREATE TABLE document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  document_id uuid NOT NULL REFERENCES clinical_documents(id) ON DELETE CASCADE,
  ord int NOT NULL,
  char_start int NOT NULL CHECK (char_start >= 0),
  char_end int NOT NULL,
  content text NOT NULL,
  tsv tsvector GENERATED ALWAYS AS
      (to_tsvector('arabic'::regconfig, content) || to_tsvector('english'::regconfig, content)) STORED,
  embedding vector(768),
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (char_end > char_start),
  UNIQUE (document_id, ord)
);
CREATE INDEX document_chunks_tsv ON document_chunks USING gin (tsv);
CREATE INDEX document_chunks_doc ON document_chunks (organization_id, document_id);

CREATE TABLE analysis_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  mode text NOT NULL CHECK (mode IN ('baseline','llm')),
  requested_mode text NOT NULL CHECK (requested_mode IN ('baseline','llm')),
  status text NOT NULL CHECK (status IN ('RUNNING','COMPLETED','FAILED')),
  policy_version text,
  fallback_reason text,
  actor_id text NOT NULL,
  result jsonb,
  started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  finished_at timestamptz
);
CREATE INDEX analysis_runs_case ON analysis_runs (authorization_request_id, started_at DESC);

ALTER TABLE clinical_facts
  ADD COLUMN analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
  ADD COLUMN label text,
  ADD COLUMN value jsonb NOT NULL DEFAULT '{{}}'::jsonb,
  ADD COLUMN quote text,
  ADD COLUMN evidence_span_id uuid REFERENCES evidence_spans(id) ON DELETE SET NULL;

ALTER TABLE authorization_evidence
  ADD COLUMN analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
  ADD COLUMN requirement_id text,
  ADD COLUMN cdi_question text,
  ADD COLUMN cdi_question_ar text;

ALTER TABLE authorization_requirements
  ADD COLUMN analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
  ADD COLUMN reason text,
  ADD COLUMN reason_ar text;

ALTER TABLE agent_runs
  ADD COLUMN analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL;
"""


def _sql(statement: str) -> None:
    dbapi_conn = op.get_bind().connection.dbapi_connection
    assert dbapi_conn is not None
    with dbapi_conn.cursor() as cur:
        cur.execute(statement)


def upgrade() -> None:
    _sql(DDL)
    for table in NEW_TABLES:
        _sql(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        _sql(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (organization_id = nullif(current_setting('app.org_id', true), '')::uuid) "
            "WITH CHECK (organization_id = nullif(current_setting('app.org_id', true), '')::uuid)"
        )
        _sql(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO mujeaz_app")


def downgrade() -> None:
    _sql(
        """
        ALTER TABLE agent_runs DROP COLUMN IF EXISTS analysis_run_id;
        ALTER TABLE authorization_requirements DROP COLUMN IF EXISTS analysis_run_id,
          DROP COLUMN IF EXISTS reason, DROP COLUMN IF EXISTS reason_ar;
        ALTER TABLE authorization_evidence DROP COLUMN IF EXISTS analysis_run_id,
          DROP COLUMN IF EXISTS requirement_id, DROP COLUMN IF EXISTS cdi_question,
          DROP COLUMN IF EXISTS cdi_question_ar;
        ALTER TABLE clinical_facts DROP COLUMN IF EXISTS analysis_run_id, DROP COLUMN IF EXISTS label,
          DROP COLUMN IF EXISTS value, DROP COLUMN IF EXISTS quote, DROP COLUMN IF EXISTS evidence_span_id;
        DROP TABLE IF EXISTS analysis_runs CASCADE;
        DROP TABLE IF EXISTS document_chunks CASCADE;
        """
    )
