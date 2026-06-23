"""Mapping Configuration for Lab Resource Manager.

Configures AutoMapper mappings between DTOs, Commands, Queries, and Resources.
"""

from neuroglia.mapping.mapper import MappingProfile


class LabInstanceMappingProfile(MappingProfile):
    """Mapping profile for lab instance resources."""

    def configure(self):
        """Configure mappings between different types."""
        # # DTO to Command mappings
        # self.create_map(CreateLabInstanceDto, CreateLabInstanceCommand) \
        #     .for_member("name", lambda src: src.name) \
        #     .for_member("namespace", lambda src: src.namespace or "default") \
        #     .for_member("lab_template", lambda src: src.lab_template) \
        #     .for_member("student_email", lambda src: src.student_email) \
        #     .for_member("duration_minutes", lambda src: src.duration_minutes) \
        #     .for_member("scheduled_start_time", lambda src: src.scheduled_start_time) \
        #     .for_member("environment", lambda src: src.environment or {})

        # # Resource to DTO mappings
        # self.create_map(LabInstanceRequest, LabInstanceDto) \
        #     .for_member("id", lambda src: src.metadata.name) \
        #     .for_member("name", lambda src: src.metadata.name) \
        #     .for_member("namespace", lambda src: src.metadata.namespace) \
        #     .for_member("created_at", lambda src: src.metadata.creation_timestamp) \
        #     .for_member("updated_at", lambda src: src.metadata.last_modified) \
        #     .for_member("lab_template", lambda src: src.spec.lab_template) \
        #     .for_member("student_email", lambda src: src.spec.student_email) \
        #     .for_member("duration_minutes", lambda src: src.spec.duration_minutes) \
        #     .for_member("scheduled_start_time", lambda src: src.spec.scheduled_start_time) \
        #     .for_member("environment", lambda src: src.spec.environment) \
        #     .for_member("phase", lambda src: src.status.phase) \
        #     .for_member("container_id", lambda src: src.status.container_id) \
        #     .for_member("started_at", lambda src: src.status.started_at) \
        #     .for_member("completed_at", lambda src: src.status.completed_at) \
        #     .for_member("error_message", lambda src: src.status.error_message) \
        #     .for_member("resource_allocation", lambda src: src.status.resource_allocation)
