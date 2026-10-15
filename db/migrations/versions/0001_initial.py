"""initial grades table + seed

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

seed = [
    (1, "Aman", "Math", 95, "A"),
    (2, "Anshu", "Math", 78, "C"),
    (3, "Akshu", "History", 88, "B"),
    (4, "Rahul", "History", 92, "A"),
    (5, "Divyansh", "Science", 85, "B"),
    (6, "Nandini", "Math", 65, "D"),
]


def upgrade() -> None:
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(), nullable=False),
    )
    op.create_index("ix_grades_subject", "grades", ["subject"])
    op.create_index("ix_grades_score", "grades", ["score"])

    # Idempotent seed for SQLite + Postgres
    bind = op.get_bind()
    existing = bind.execute(sa.text("SELECT id FROM grades")).fetchall()
    existing_ids = {r[0] for r in existing}
    for row in seed:
        if row[0] not in existing_ids:
            bind.execute(
                sa.text("INSERT INTO grades (id, name, subject, score, grade) "
                        "VALUES (:id, :name, :subject, :score, :grade)"),
                {"id": row[0], "name": row[1], "subject": row[2], "score": row[3], "grade": row[4]},
            )


def downgrade() -> None:
    op.drop_index("ix_grades_score", table_name="grades")
    op.drop_index("ix_grades_subject", table_name="grades")
    op.drop_table("grades")
