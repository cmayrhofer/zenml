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

import pytest

from tests.integration.examples.utils import run_example


def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the great_expectations_data_validation example."""
    with run_example(
        request=request,
        name="great_expectations_data_validation",
        pipeline_name="validation_pipeline",
        step_count=6,
        run_count=1,
    ):
        pass
