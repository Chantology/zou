from sqlalchemy_utils import UUIDType

from zou.app import db
from zou.app.models.serializer import SerializerMixin
from zou.app.models.base import BaseMixin


class ScheduleSegment(db.Model, BaseMixin, SerializerMixin):
    """
    A continuous stretch of a schedule bar, for a task or for a schedule
    item (a department or a sequence row).

    A bar carrying no segment at all spans its own start and end date, which
    is the normal uncut case. Cutting it stores the pieces here instead, and
    the interruptions are then the space left between two of them. Storing
    the pieces rather than the gaps is what lets each of them be moved on
    its own: a drag writes the dates of one segment and leaves its
    neighbours alone.

    Exactly one owner is set. Both columns cascade, so segments disappear
    with the task or the schedule item they belong to.
    """

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    task_id = db.Column(
        UUIDType(binary=False),
        db.ForeignKey("task.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    schedule_item_id = db.Column(
        UUIDType(binary=False),
        db.ForeignKey("schedule_item.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    __table_args__ = (
        db.CheckConstraint(
            "start_date <= end_date", name="schedule_segment_date_check"
        ),
        # IS NULL never yields NULL, so this is a plain exclusive or: it
        # rejects both owners being set as well as neither.
        db.CheckConstraint(
            "(task_id IS NULL) != (schedule_item_id IS NULL)",
            name="schedule_segment_owner_check",
        ),
    )
