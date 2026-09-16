"""Add schedule segments

Revision ID: a70fd7b4e2e1
Revises: a3f7c2d91b45
Create Date: 2026-08-14 15:42:39.367915

"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import uuid

# revision identifiers, used by Alembic.
revision = "a70fd7b4e2e1"
down_revision = "a3f7c2d91b45"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "schedule_segment",
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "task_id",
            sqlalchemy_utils.types.uuid.UUIDType(binary=False),
            default=uuid.uuid4,
            nullable=True,
        ),
        sa.Column(
            "schedule_item_id",
            sqlalchemy_utils.types.uuid.UUIDType(binary=False),
            default=uuid.uuid4,
            nullable=True,
        ),
        sa.Column(
            "id",
            sqlalchemy_utils.types.uuid.UUIDType(binary=False),
            default=uuid.uuid4,
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "(task_id IS NULL) != (schedule_item_id IS NULL)",
            name="schedule_segment_owner_check",
        ),
        sa.CheckConstraint(
            "start_date <= end_date", name="schedule_segment_date_check"
        ),
        sa.ForeignKeyConstraint(
            ["schedule_item_id"], ["schedule_item.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("schedule_segment", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_schedule_segment_schedule_item_id"),
            ["schedule_item_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_schedule_segment_task_id"),
            ["task_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("schedule_segment", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_schedule_segment_task_id"))
        batch_op.drop_index(batch_op.f("ix_schedule_segment_schedule_item_id"))

    op.drop_table("schedule_segment")
