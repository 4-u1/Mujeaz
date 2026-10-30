"""M3 readiness: physician documentation queries and case-linked addenda.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-30
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ORG = "organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE"

DDL = f"""
CREATE TABLE documentation_queries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {ORG},
  authorization_request_id uuid NOT NULL REFERENCES authorization_requests(id) ON DELETE CASCADE,
  requirement_id text NOT NULL,
  question text NOT NULL,
  question_ar text,
  status text NOT NULL CHECK (status IN ('OPEN','ANSWERED','DECLINED','WITHDRAWN')),
  assignee_role text NOT NULL DEFAULT 'physician',
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  due_on date,
  analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
  closed_by text,
  closed_at timestamptz,
  answer jsonb,
  decline_reason text
);
CREATE UNIQUE INDEX documentation_queries_one_open
  ON documentation_queries (authorization_request_id, requirement_id) WHERE status = 'OPEN';
CREATE INDEX documentation_queries_status ON documentation_queries (organization_id, status, created_at);

ALTER TABLE clinical_documents
  ADD COLUMN authorization_request_id uuid REFERENCES authorization_requests(id) ON DELETE CASCADE,
  ADD COLUMN author_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN signed_at timestamptz,
  ADD COLUMN query_id uuid REFERENCES documentation_queries(id) ON DELETE SET NULL;

ALTER TABLE documentation_queries
  ADD COLUMN addendum_document_id uuid REFERENCES clinical_documents(id) ON DELETE SET NULL;
"""


def _sql(statement: str) -> None:
    dbapi_conn = op.get_bind().connection.dbapi_connection
    assert dbapi_conn is not None
    with dbapi_conn.cursor() as cur:
        cur.execute(statement)


def upgrade() -> None:
    _sql(DDL)
    _sql("ALTER TABLE documentation_queries ENABLE ROW LEVEL SECURITY")
    _sql(
        "CREATE POLICY tenant_isolation ON documentation_queries "
        "USING (organization_id = nullif(current_setting('app.org_id', true), '')::uuid) "
        "WITH CHECK (organization_id = nullif(current_setting('app.org_id', true), '')::uuid)"
    )
    _sql("GRANT SELECT, INSERT, UPDATE, DELETE ON documentation_queries TO mujeaz_app")


def downgrade() -> None:
    _sql(
        """
        ALTER TABLE documentation_queries DROP COLUMN IF EXISTS addendum_document_id;
        ALTER TABLE clinical_documents DROP COLUMN IF EXISTS query_id, DROP COLUMN IF EXISTS signed_at,
          DROP COLUMN IF EXISTS author_user_id, DROP COLUMN IF EXISTS authorization_request_id;
        DROP TABLE IF EXISTS documentation_queries CASCADE;
        """
    )
