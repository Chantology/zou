from flask_jwt_extended import jwt_required

from zou.app.models.schedule_segment import ScheduleSegment

from zou.app.blueprints.crud.base import BaseModelsResource, BaseModelResource

from zou.app.services import (
    permissions_service,
    schedule_service,
    tasks_service,
)

from zou.app.services.exception import WrongParameterException


def _check_owner_access(data):
    """
    Allow the operation when the user can supervise the task the segment
    belongs to, or manage the production of its schedule item. The project
    access check comes first: it resolves the per project role that the
    checks after it read.
    """
    task_id = data.get("task_id")
    schedule_item_id = data.get("schedule_item_id")
    if task_id:
        task = tasks_service.get_task(task_id)
        permissions_service.check_project_access(task["project_id"])
        permissions_service.check_supervisor_task_access(task)
    elif schedule_item_id:
        schedule_item = schedule_service.get_schedule_item(schedule_item_id)
        permissions_service.check_project_access(schedule_item["project_id"])
        permissions_service.check_supervisor_project_task_type_access(
            schedule_item["project_id"], schedule_item["task_type_id"]
        )
    else:
        raise WrongParameterException(
            "A segment belongs either to a task or to a schedule item"
        )
    return True


def _check_no_overlap(data, exclude_id=None):
    """
    A bar holds several segments, but two of them may not cover the same
    day: that would be the same work planned twice.
    """
    if schedule_service.get_schedule_segments_between(
        data["start_date"],
        data["end_date"],
        task_id=data.get("task_id"),
        schedule_item_id=data.get("schedule_item_id"),
        exclude_id=exclude_id,
    ):
        raise WrongParameterException(
            "A segment already exists for this period"
        )


class ScheduleSegmentsResource(BaseModelsResource):
    def __init__(self):
        BaseModelsResource.__init__(self, ScheduleSegment)

    def check_create_permissions(self, data):
        return _check_owner_access(data)

    def check_creation_integrity(self, data):
        _check_no_overlap(data)
        return data

    @jwt_required()
    def get(self):
        """
        Get schedule segments
        ---
        tags:
          - Crud
        description: Retrieve all schedule segments. Supports filtering via
          query parameters and pagination.
        parameters:
          - in: query
            name: task_id
            required: false
            schema:
              type: string
              format: uuid
            description: Restrict the result to one task
          - in: query
            name: schedule_item_id
            required: false
            schema:
              type: string
              format: uuid
            description: Restrict the result to one schedule item
        responses:
            200:
              description: Schedule segments retrieved successfully
            400:
              description: Invalid filter format or query error
        """
        return super().get()

    @jwt_required()
    def post(self):
        """
        Create schedule segment
        ---
        tags:
          - Crud
        description: Create a piece of a schedule bar. Both bounds are
          inclusive. Exactly one of task_id and schedule_item_id is
          expected. A bar can hold several segments as long as they do not
          overlap.
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                required:
                  - start_date
                  - end_date
                properties:
                  start_date:
                    type: string
                    format: date
                    example: "2024-01-15"
                  end_date:
                    type: string
                    format: date
                    example: "2024-01-20"
                  description:
                    type: string
                    example: First pass
                  task_id:
                    type: string
                    format: uuid
                    example: a24a6ea4-ce75-4665-a070-57453082c25
                  schedule_item_id:
                    type: string
                    format: uuid
                    example: b24a6ea4-ce75-4665-a070-57453082c25
        responses:
            201:
              description: Schedule segment created successfully
            400:
              description: Invalid data format or overlapping segment
        """
        return super().post()


class ScheduleSegmentResource(BaseModelResource):
    def __init__(self):
        BaseModelResource.__init__(self, ScheduleSegment)
        # The permission hooks below read the owner from the stored
        # instance, so a PUT body must not be able to move the segment onto
        # another task or another production.
        self.protected_fields += ["task_id", "schedule_item_id"]

    def check_read_permissions(self, instance_dict):
        return _check_owner_access(instance_dict)

    def check_update_permissions(self, instance_dict, data):
        return _check_owner_access(instance_dict)

    def check_delete_permissions(self, instance_dict):
        return _check_owner_access(instance_dict)

    def pre_update(self, instance_dict, data):
        _check_no_overlap(
            {
                "start_date": data.get(
                    "start_date", instance_dict["start_date"]
                ),
                "end_date": data.get("end_date", instance_dict["end_date"]),
                "task_id": instance_dict["task_id"],
                "schedule_item_id": instance_dict["schedule_item_id"],
            },
            exclude_id=instance_dict["id"],
        )
        return data

    @jwt_required()
    def get(self, instance_id):
        """
        Get schedule segment
        ---
        tags:
          - Crud
        description: Retrieve a schedule segment by its ID.
        parameters:
          - in: path
            name: instance_id
            required: true
            schema:
              type: string
              format: uuid
            example: a24a6ea4-ce75-4665-a070-57453082c25
        responses:
            200:
              description: Schedule segment retrieved successfully
            400:
              description: Invalid ID format or query error
        """
        return super().get(instance_id)

    @jwt_required()
    def put(self, instance_id):
        """
        Update schedule segment
        ---
        tags:
          - Crud
        description: Update a schedule segment with data provided in the
          request body. The bar it belongs to cannot be changed.
        parameters:
          - in: path
            name: instance_id
            required: true
            schema:
              type: string
              format: uuid
            example: a24a6ea4-ce75-4665-a070-57453082c25
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  start_date:
                    type: string
                    format: date
                    example: "2024-01-16"
                  end_date:
                    type: string
                    format: date
                    example: "2024-01-21"
                  description:
                    type: string
                    example: First pass
        responses:
            200:
              description: Schedule segment updated successfully
            400:
              description: Invalid data format or overlapping segment
        """
        return super().put(instance_id)

    @jwt_required()
    def delete(self, instance_id):
        """
        Delete schedule segment
        ---
        tags:
          - Crud
        description: Delete a schedule segment by its ID.
        parameters:
          - in: path
            name: instance_id
            required: true
            schema:
              type: string
              format: uuid
            example: a24a6ea4-ce75-4665-a070-57453082c25
        responses:
            204:
              description: Schedule segment deleted successfully
            400:
              description: Integrity error or cannot delete
        """
        return super().delete(instance_id)
