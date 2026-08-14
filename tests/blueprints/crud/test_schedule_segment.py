from tests.base import ApiDBTestCase

from zou.app.models.schedule_item import ScheduleItem
from zou.app.utils import fields


class ScheduleSegmentTestCase(ApiDBTestCase):
    def setUp(self):
        super().setUp()
        self.generate_fixture_project_status()
        self.generate_fixture_project()
        self.generate_fixture_asset_type()
        self.generate_fixture_asset()
        self.generate_fixture_department()
        self.generate_fixture_task_type()
        self.generate_fixture_task_status()
        self.generate_fixture_task()
        self.task_id = str(self.task.id)
        self.schedule_item = ScheduleItem.create(
            project_id=self.project.id,
            task_type_id=self.task_type.id,
            start_date="2024-01-01",
            end_date="2024-02-01",
        )
        self.schedule_item_id = str(self.schedule_item.id)

    def segment(self, start, end=None, expected_status=201, **data):
        payload = {"start_date": start, "end_date": end or start, **data}
        payload.setdefault("task_id", self.task_id)
        return self.post("data/schedule-segments", payload, expected_status)

    def test_get_schedule_segments(self):
        self.segment("2024-01-15")
        self.assertEqual(len(self.get("data/schedule-segments")), 1)

    def test_get_schedule_segment(self):
        segment = self.segment("2024-01-15")
        again = self.get(f"data/schedule-segments/{segment['id']}")
        self.assertEqual(segment["id"], again["id"])
        self.get_404(f"data/schedule-segments/{fields.gen_uuid()}")

    def test_create_schedule_segment(self):
        segment = self.segment(
            "2024-01-15", "2024-01-18", description="First pass"
        )
        self.assertIsNotNone(segment["id"])
        self.assertEqual(segment["start_date"], "2024-01-15")
        self.assertEqual(segment["end_date"], "2024-01-18")
        self.assertEqual(segment["description"], "First pass")

    def test_update_schedule_segment(self):
        segment = self.segment("2024-01-15")
        self.put(
            f"data/schedule-segments/{segment['id']}",
            {"end_date": "2024-01-18"},
        )
        again = self.get(f"data/schedule-segments/{segment['id']}")
        self.assertEqual(again["end_date"], "2024-01-18")

    def test_delete_schedule_segment(self):
        segment = self.segment("2024-01-15")
        self.delete(f"data/schedule-segments/{segment['id']}")
        self.assertEqual(self.get("data/schedule-segments"), [])

    def test_a_bar_holds_several_segments(self):
        """
        The point of cutting a bar: the pieces are stored side by side and
        the interruption is the space left between them.
        """
        self.segment("2024-01-15", "2024-01-17")
        self.segment("2024-01-22", "2024-01-25")
        self.segment("2024-02-01")
        segments = self.get(f"data/schedule-segments?task_id={self.task_id}")
        self.assertEqual(len(segments), 3)

    def test_two_segments_of_a_bar_cannot_overlap(self):
        self.segment("2024-01-15", "2024-01-18")
        self.segment("2024-01-10", "2024-01-15", expected_status=400)
        self.segment("2024-01-18", "2024-01-20", expected_status=400)
        self.segment("2024-01-01", "2024-01-31", expected_status=400)
        self.segment("2024-01-19", "2024-01-20")

    def test_a_segment_does_not_overlap_itself_on_update(self):
        segment = self.segment("2024-01-15", "2024-01-16")
        self.put(
            f"data/schedule-segments/{segment['id']}",
            {"start_date": "2024-01-15", "end_date": "2024-01-18"},
        )
        self.assertEqual(
            self.get(f"data/schedule-segments/{segment['id']}")["end_date"],
            "2024-01-18",
        )

    def test_segments_of_different_bars_may_overlap(self):
        """
        Two tasks running over the same days is the normal case, the
        overlap check is scoped to one bar.
        """
        self.segment("2024-01-15", "2024-01-18")
        self.segment(
            "2024-01-15",
            "2024-01-18",
            task_id=None,
            schedule_item_id=self.schedule_item_id,
        )
        self.assertEqual(len(self.get("data/schedule-segments")), 2)

    def test_a_segment_belongs_to_a_schedule_item(self):
        segment = self.segment(
            "2024-01-15",
            "2024-01-18",
            task_id=None,
            schedule_item_id=self.schedule_item_id,
        )
        self.assertEqual(segment["schedule_item_id"], self.schedule_item_id)
        self.assertIsNone(segment["task_id"])

    def test_a_segment_needs_exactly_one_owner(self):
        self.segment("2024-01-15", task_id=None, expected_status=400)
        self.segment(
            "2024-01-15",
            schedule_item_id=self.schedule_item_id,
            expected_status=400,
        )

    def test_the_owner_cannot_be_changed(self):
        """
        The permission hooks read the owner from the stored instance, so
        letting a PUT move the row would sidestep them.
        """
        segment = self.segment("2024-01-15")
        self.put(
            f"data/schedule-segments/{segment['id']}",
            {"task_id": None, "schedule_item_id": self.schedule_item_id},
        )
        again = self.get(f"data/schedule-segments/{segment['id']}")
        self.assertEqual(again["task_id"], self.task_id)
        self.assertIsNone(again["schedule_item_id"])

    def test_segments_go_away_with_their_task(self):
        segment = self.segment("2024-01-15")
        self.delete(f"data/tasks/{self.task_id}")
        self.get_404(f"data/schedule-segments/{segment['id']}")

    def test_segments_go_away_with_their_schedule_item(self):
        segment = self.segment(
            "2024-01-15",
            task_id=None,
            schedule_item_id=self.schedule_item_id,
        )
        self.delete(f"data/schedule-items/{self.schedule_item_id}")
        self.get_404(f"data/schedule-segments/{segment['id']}")


class ProductionScheduleSegmentsTestCase(ApiDBTestCase):
    """
    The schedule pulls every segment of a production in one request.
    """

    def setUp(self):
        super().setUp()
        self.generate_fixture_project_status()
        self.generate_fixture_project()
        self.generate_fixture_asset_type()
        self.generate_fixture_asset()
        self.generate_fixture_department()
        self.generate_fixture_task_type()
        self.generate_fixture_task_status()
        self.generate_fixture_task()
        self.generate_fixture_shot()
        self.shot_task = self.generate_fixture_shot_task()
        self.project_id = str(self.project.id)
        self.schedule_item = ScheduleItem.create(
            project_id=self.project.id,
            task_type_id=self.task_type.id,
            start_date="2024-01-01",
            end_date="2024-02-01",
        )

    def add_segment(self, start, **owner):
        return self.post(
            "data/schedule-segments",
            {"start_date": start, "end_date": start, **owner},
        )

    def test_segments_of_tasks_and_schedule_items_come_together(self):
        self.add_segment("2024-01-15", task_id=str(self.task.id))
        self.add_segment("2024-01-16", task_id=str(self.shot_task.id))
        self.add_segment(
            "2024-01-17", schedule_item_id=str(self.schedule_item.id)
        )
        segments = self.get(
            f"data/projects/{self.project_id}/schedule-segments"
        )
        self.assertEqual(len(segments), 3)

    def test_segments_are_sorted_by_start_date(self):
        self.add_segment("2024-02-01", task_id=str(self.task.id))
        self.add_segment("2024-01-05", task_id=str(self.shot_task.id))
        segments = self.get(
            f"data/projects/{self.project_id}/schedule-segments"
        )
        self.assertEqual(
            [segment["start_date"] for segment in segments],
            ["2024-01-05", "2024-02-01"],
        )

    def test_segments_can_be_filtered_by_task_type(self):
        self.add_segment("2024-01-15", task_id=str(self.task.id))
        self.add_segment("2024-01-16", task_id=str(self.shot_task.id))
        segments = self.get(
            f"data/projects/{self.project_id}/schedule-segments"
            f"?task_type_id={self.shot_task.task_type_id}"
        )
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["task_id"], str(self.shot_task.id))
