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
"""Abstract base class for all ZenML pipelines."""

import inspect
from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Tuple,
    Type,
    Union,
    cast,
)

from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.exceptions import PipelineInterfaceError
from zenml.logger import get_logger
from zenml.pipelines.new.pipeline import Pipeline
from zenml.steps import BaseStep
from zenml.steps.base_step import BaseStepMeta

if TYPE_CHECKING:

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]

logger = get_logger(__name__)
PIPELINE_INNER_FUNC_NAME = "connect"
PARAM_ENABLE_CACHE = "enable_cache"
PARAM_ENABLE_ARTIFACT_METADATA = "enable_artifact_metadata"
INSTANCE_CONFIGURATION = "INSTANCE_CONFIGURATION"
PARAM_SETTINGS = "settings"
PARAM_EXTRA_OPTIONS = "extra"


class PipelineTemplateMeta(type):
    """Pipeline Metaclass responsible for validating the pipeline definition."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "PipelineTemplateMeta":
        """Saves argument names for later verification purposes.

        Args:
            name: The name of the class.
            bases: The base classes of the class.
            dct: The dictionary of the class.

        Returns:
            The class.
        """
        dct.setdefault(INSTANCE_CONFIGURATION, {})
        cls = cast(
            Type["PipelineTemplate"], super().__new__(mcs, name, bases, dct)
        )

        cls.STEP_SPEC = {}

        connect_spec = inspect.getfullargspec(
            inspect.unwrap(getattr(cls, PIPELINE_INNER_FUNC_NAME))
        )
        connect_args = connect_spec.args

        if connect_args and connect_args[0] == "self":
            connect_args.pop(0)

        for arg in connect_args:
            arg_type = connect_spec.annotations.get(arg, None)
            cls.STEP_SPEC.update({arg: arg_type})
        return cls


class PipelineTemplate(Pipeline, metaclass=PipelineTemplateMeta):
    STEP_SPEC: ClassVar[Dict[str, Any]] = None  # type: ignore[assignment]

    INSTANCE_CONFIGURATION: Dict[str, Any] = {}

    def __init__(self, *args: BaseStep, **kwargs: Any) -> None:
        """Initialize the BasePipeline.

        Args:
            *args: The steps to be executed by this pipeline.
            **kwargs: The configuration for this pipeline.
        """
        kwargs.update(self.INSTANCE_CONFIGURATION)
        super().__init__(
            enable_cache=kwargs.pop(PARAM_ENABLE_CACHE, None),
            enable_artifact_metadata=kwargs.pop(
                PARAM_ENABLE_ARTIFACT_METADATA, None
            ),
        )

        self._apply_class_configuration(kwargs)
        self._verify_steps(*args, **kwargs)

    def _apply_class_configuration(self, options: Dict[str, Any]) -> None:
        """Applies the configurations specified on the pipeline class.

        Args:
            options: Class configurations.
        """
        settings = options.pop(PARAM_SETTINGS, None)
        extra = options.pop(PARAM_EXTRA_OPTIONS, None)
        self.configure(settings=settings, extra=extra)

    def _verify_steps(self, *steps: BaseStep, **kw_steps: Any) -> None:
        """Verifies the initialization args and kwargs of this pipeline.

        This method makes sure that no missing/unexpected arguments or
        arguments of a wrong type are passed when creating a pipeline. If
        all arguments are correct, saves the steps to `self.__steps`.

        Args:
            *steps: The args passed to the init method of this pipeline.
            **kw_steps: The kwargs passed to the init method of this pipeline.

        Raises:
            PipelineInterfaceError: If there are too many/few arguments or
                arguments with a wrong name/type.
        """
        input_step_keys = list(self.STEP_SPEC.keys())
        if len(steps) > len(input_step_keys):
            raise PipelineInterfaceError(
                f"Too many input steps for pipeline '{self.name}'. "
                f"This pipeline expects {len(input_step_keys)} step(s) "
                f"but got {len(steps) + len(kw_steps)}."
            )

        combined_steps = {}
        step_ids: Dict[int, str] = {}

        def _verify_step(key: str, step: BaseStep) -> None:
            """Verifies a single step of the pipeline.

            Args:
                key: The key of the step.
                step: The step to verify.

            Raises:
                PipelineInterfaceError: If the step is not of the correct type
                    or is of the same class as another step.
            """
            step_class = type(step)

            if isinstance(step, BaseStepMeta):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{step_class}`) for argument "
                    f"'{key}' of pipeline '{self.name}'. "
                    f"A `BaseStep` subclass was provided instead of an "
                    f"instance. "
                    f"This might have been caused due to missing brackets of "
                    f"your steps when creating a pipeline with `@step` "
                    f"decorated functions, "
                    f"for which the correct syntax is `pipeline(step=step())`."
                )

            if not isinstance(step, BaseStep):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{step_class}`) for argument "
                    f"'{key}' of pipeline '{self.name}'. Only "
                    f"`@step` decorated functions or instances of `BaseStep` "
                    f"subclasses can be used as arguments when creating "
                    f"a pipeline."
                )

            if id(step) in step_ids:
                previous_key = step_ids[id(step)]
                raise PipelineInterfaceError(
                    f"Found the same step object for arguments "
                    f"'{previous_key}' and '{key}' in pipeline '{self.name}'. "
                    "Step object cannot be reused inside a ZenML pipeline. "
                    "A possible solution is to create two instances of the "
                    "same step class and assigning them different names: "
                    "`first_instance = step_class(name='s1')` and "
                    "`second_instance = step_class(name='s2')`."
                )

            step.pipeline_parameter_name = key
            step_ids[id(step)] = key
            combined_steps[key] = step

        # verify args
        for i, step in enumerate(steps):
            key = input_step_keys[i]
            _verify_step(key, step)

        # verify kwargs
        for key, step in kw_steps.items():
            if key in combined_steps:
                # a step for this key was already set by
                # the positional input steps
                raise PipelineInterfaceError(
                    f"Unexpected keyword argument '{key}' for pipeline "
                    f"'{self.name}'. A step for this key was "
                    f"already passed as a positional argument."
                )
            _verify_step(key, step)

        # check if there are any missing or unexpected steps
        expected_steps = set(self.STEP_SPEC.keys())
        actual_steps = set(combined_steps.keys())
        missing_steps = expected_steps - actual_steps
        unexpected_steps = actual_steps - expected_steps

        if missing_steps:
            raise PipelineInterfaceError(
                f"Missing input step(s) for pipeline "
                f"'{self.name}': {missing_steps}."
            )

        if unexpected_steps:
            raise PipelineInterfaceError(
                f"Unexpected input step(s) for pipeline "
                f"'{self.name}': {unexpected_steps}. This pipeline "
                f"only requires the following steps: {expected_steps}."
            )

        self._steps = combined_steps

    @abstractmethod
    def connect(self, *args: BaseStep, **kwargs: BaseStep) -> None:
        """Function that connects inputs and outputs of the pipeline steps.

        Args:
            *args: The positional arguments passed to the pipeline.
            **kwargs: The keyword arguments passed to the pipeline.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError
