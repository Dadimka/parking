"""add_detections_table

Revision ID: cb1e03d70c15
Revises: e7532876441e
Create Date: 2025-12-17 00:05:51.732044

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cb1e03d70c15"
down_revision: Union[str, None] = "e7532876441e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create detections table
    op.create_table(
        "detections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("camera_id", sa.UUID(), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=False),
        sa.Column("frame_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("offset_seconds", sa.Float(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("class_name", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("bbox_normalized", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for better query performance
    op.create_index("ix_detections_video_id", "detections", ["video_id"])
    op.create_index("ix_detections_camera_id", "detections", ["camera_id"])
    op.create_index("ix_detections_frame_number", "detections", ["frame_number"])
    op.create_index("ix_detections_class_name", "detections", ["class_name"])
    op.create_index("ix_detections_frame_time", "detections", ["frame_time"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_detections_frame_time", table_name="detections")
    op.drop_index("ix_detections_class_name", table_name="detections")
    op.drop_index("ix_detections_frame_number", table_name="detections")
    op.drop_index("ix_detections_camera_id", table_name="detections")
    op.drop_index("ix_detections_video_id", table_name="detections")

    # Drop table
    op.drop_table("detections")
