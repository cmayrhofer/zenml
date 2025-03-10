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
import os
from typing import Type

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.steps import BaseParameters, Output, step


class SomeObj:
    def __init__(self, name: str):
        self.name = name


class SomeMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (SomeObj,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def load(self, data_type: Type[SomeObj]) -> SomeObj:
        super().load(data_type)
        with fileio.open(os.path.join(self.uri, "data.txt"), "r") as f:
            name = f.read()
        return SomeObj(name=name)

    def save(self, my_obj: SomeObj) -> None:
        super().save(my_obj)
        with fileio.open(os.path.join(self.uri, "data.txt"), "w") as f:
            f.write(my_obj.name)


class StepParams(BaseParameters):
    some_option: int = 4


@step
def some_step(params: StepParams) -> Output(output_1=SomeObj, output_2=int):
    return SomeObj("Custom-Object"), params.some_option


@pipeline(enable_cache=False)
def some_pipe(
    step_1,
):
    step_1()
