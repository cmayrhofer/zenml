#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Pipeline deployment."""
from typing import Any, Dict, Optional
from uuid import UUID

import zenml
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.schedule import Schedule
from zenml.config.step_configurations import Step
from zenml.config.strict_base_model import StrictBaseModel
from zenml.utils import pydantic_utils


class PipelineDeployment(
    StrictBaseModel, pydantic_utils.YAMLSerializationMixin
):
    """Class representing the deployment of a ZenML pipeline."""

    run_name: str
    schedule: Optional[Schedule] = None
    schedule_id: Optional[UUID] = None
    stack_id: UUID
    pipeline: PipelineConfiguration
    pipeline_id: Optional[UUID] = None
    steps: Dict[str, Step] = {}
    zenml_version: str = zenml.__version__
    client_environment: Dict[str, str] = {}

    def add_extra(self, key: str, value: Any) -> None:
        """Adds an extra key-value pair to the pipeline configuration.

        Args:
            key: Key for which to add the extra value.
            value: The extra value.
        """
        self.pipeline.extra[key] = value
