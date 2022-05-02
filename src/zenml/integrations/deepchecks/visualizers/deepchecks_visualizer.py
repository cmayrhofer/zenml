#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import tempfile
import webbrowser
from abc import abstractmethod
from typing import Any

from deepchecks.core.suite import SuiteResult

from zenml.artifacts import DataAnalysisArtifact
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseStepVisualizer

logger = get_logger(__name__)


class DeepchecksVisualizer(BaseStepVisualizer):
    """The implementation of a Deepchecks Visualizer."""

    @abstractmethod
    def visualize(self, object: StepView, *args: Any, **kwargs: Any) -> None:
        """Method to visualize components.

        Args:
            object: StepView fetched from run.get_step().
        """
        for artifact_view in object.outputs.values():
            # filter out anything but data analysis artifacts
            if artifact_view.type == DataAnalysisArtifact.__name__:
                artifact = artifact_view.read()
                self.generate_report(artifact)

    def generate_report(self, result: SuiteResult) -> None:
        """Generate a Deepchecks Report.

        Args:
            result: A SuiteResult.
        """
        print(result)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".html", encoding="utf-8"
        ) as f:
            result.save_as_html(f)
            file_name = f.name

        with open(file_name, "r") as f:
            html_ = f.read()

        if Environment.in_notebook():
            from IPython.core.display import HTML, display

            display(HTML(html_))
        else:
            logger.warning(
                "The magic functions are only usable in a Jupyter notebook."
            )
            url = f"file:///{f.name}"
            logger.info("Opening %s in a new browser.." % f.name)
            webbrowser.open(url, new=2)
