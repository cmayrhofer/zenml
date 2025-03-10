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
from contextlib import ExitStack as does_not_raise
from typing import Type
from uuid import uuid4

import pytest
from pydantic import ValidationError, validator

from zenml.enums import StackComponentType
from zenml.models import ComponentRequestModel
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestrator,
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManagerConfig,
)
from zenml.stack.flavor_registry import flavor_registry


def test_stack_component_default_method_implementations(stub_component):
    """Tests the return values for default implementations of some StackComponent methods."""
    assert stub_component.validator is None
    assert stub_component.log_file is None
    assert stub_component.settings_class is None
    assert stub_component.requirements == set()

    assert stub_component.is_provisioned is True
    assert stub_component.is_running is True

    with pytest.raises(NotImplementedError):
        stub_component.provision()

    with pytest.raises(NotImplementedError):
        stub_component.deprovision()

    with pytest.raises(NotImplementedError):
        stub_component.resume()

    with pytest.raises(NotImplementedError):
        stub_component.suspend()


def test_stack_component_dict_only_contains_public_attributes(
    stub_component_config,
):
    """Tests that the `dict()` method which is used to serialize stack components does not include private attributes."""
    assert stub_component_config._some_private_attribute_name == "Also Aria"

    expected_dict_keys = {"some_public_attribute_name"}
    assert set(stub_component_config.dict().keys()) == expected_dict_keys


def test_stack_component_public_attributes_are_immutable(
    stub_component_config,
):
    """Tests that stack component public attributes are immutable but private attribute can be modified."""
    with pytest.raises(TypeError):
        stub_component_config.some_public_attribute_name = "Not Aria"

    with does_not_raise():
        stub_component_config._some_private_attribute_name = "Woof"


def test_stack_component_prevents_extra_attributes(stub_component_config):
    """Tests that passing extra attributes to a StackComponent fails."""
    component_class = stub_component_config.__class__

    with does_not_raise():
        component_class(some_public_attribute_name="test")

    with pytest.raises(ValidationError):
        component_class(not_an_attribute_name="test")


class StubOrchestratorConfig(BaseOrchestratorConfig):
    attribute_without_validator: str = ""
    attribute_with_validator: str = ""

    @validator("attribute_with_validator")
    def _ensure_something(cls, value):
        return value


class StubOrchestrator(BaseOrchestrator):
    @property
    def config(self) -> StubOrchestratorConfig:
        return self._config

    def prepare_or_run_pipeline(self, **kwargs):
        pass

    def get_orchestrator_run_id(self) -> str:
        return "some_run_id"


class StubOrchestratorFlavor(BaseOrchestratorFlavor):
    @property
    def name(self) -> str:
        return "TEST"

    @property
    def config_class(self) -> Type[StubOrchestratorConfig]:
        return StubOrchestratorConfig

    @property
    def implementation_class(self) -> Type[StubOrchestrator]:
        return StubOrchestrator


def _get_stub_orchestrator(name, repo=None, **kwargs) -> ComponentRequestModel:
    return ComponentRequestModel(
        name=name,
        configuration=StubOrchestratorConfig(**kwargs),
        flavor="TEST",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4() if repo is None else repo.active_user.id,
        workspace=uuid4() if repo is None else repo.active_workspace.id,
    )


@pytest.fixture
def register_stub_orchestrator_flavor() -> None:
    """Create the stub orchestrator flavor temporarily."""
    flavor = StubOrchestratorFlavor()

    flavor_registry._register_flavor(flavor.to_model())
    yield None
    flavor_registry._flavors[flavor.type].pop(flavor.name)


def test_stack_component_prevents_secret_references_for_some_attributes(
    clean_client, register_stub_orchestrator_flavor
):
    """Tests that the stack component prevents secret references for the name attribute and all attributes with associated pydantic validators."""
    with pytest.raises(ValueError):
        # Can't have a secret reference for the name
        _get_stub_orchestrator(name="{{secret.key}}")

    with pytest.raises(ValueError):
        # Can't have a secret reference for an attribute that requires
        # pydantic validation
        clean_client.create_stack_component(
            name="test",
            configuration={"attribute_with_validator": "{{secret.key}}"},
            flavor="TEST",
            component_type=StackComponentType.ORCHESTRATOR,
        )

    with does_not_raise():
        clean_client.create_stack_component(
            name="test",
            configuration={"attribute_without_validator": "{{secret.key}}"},
            flavor="TEST",
            component_type=StackComponentType.ORCHESTRATOR,
        )


def test_stack_component_secret_reference_resolving(
    clean_client, register_stub_orchestrator_flavor
):
    """Tests that the stack component resolves secrets if possible."""
    from zenml.artifact_stores import LocalArtifactStoreConfig

    new_artifact_store = clean_client.create_stack_component(
        name="local",
        configuration=LocalArtifactStoreConfig().dict(),
        flavor="local",
        component_type=StackComponentType.ARTIFACT_STORE,
    )
    new_orchestrator = clean_client.create_stack_component(
        name="stub_orchestrator",
        component_type=StackComponentType.ORCHESTRATOR,
        configuration=StubOrchestratorConfig(
            attribute_without_validator="{{secret.key}}"
        ).dict(),
        flavor="TEST",
    )

    new_stack = clean_client.create_stack(
        name="new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: new_artifact_store.name,
            StackComponentType.ORCHESTRATOR: new_orchestrator.name,
        },
    )

    with pytest.raises(RuntimeError):
        # not part of the active stack
        o = StubOrchestrator.from_model(new_orchestrator)
        _ = o.config.attribute_without_validator

    clean_client.activate_stack(new_stack.id)

    with pytest.raises(RuntimeError):
        # no secret manager in stack
        o = StubOrchestrator.from_model(new_orchestrator)
        _ = o.config.attribute_without_validator

    from zenml.secrets_managers import LocalSecretsManager

    new_secrets_manager = clean_client.create_stack_component(
        name="new_secrets_manager",
        component_type=StackComponentType.SECRETS_MANAGER,
        flavor="local",
        configuration=LocalSecretsManagerConfig().dict(),
    )

    clean_client.update_stack(
        name_id_or_prefix=new_stack.id,
        component_updates={
            StackComponentType.SECRETS_MANAGER: [new_secrets_manager.name]
        },
    )

    with pytest.raises(KeyError):
        # secret doesn't exist
        o = StubOrchestrator.from_model(new_orchestrator)
        _ = o.config.attribute_without_validator

    from zenml.secret import ArbitrarySecretSchema

    secret_without_correct_key = ArbitrarySecretSchema(
        name="secret", wrong_key="value"
    )

    x = LocalSecretsManager.from_model(new_secrets_manager)
    x.register_secret(secret_without_correct_key)

    with pytest.raises(KeyError):
        # key doesn't exist
        o = StubOrchestrator.from_model(new_orchestrator)
        _ = o.config.attribute_without_validator

    secret_with_correct_key = ArbitrarySecretSchema(name="secret", key="value")
    x.update_secret(secret_with_correct_key)

    with does_not_raise():
        o = StubOrchestrator.from_model(new_orchestrator)
        assert o.config.attribute_without_validator == "value"


def test_stack_component_serialization_does_not_resolve_secrets(
    clean_client, register_stub_orchestrator_flavor
):
    """Tests that all the serialization methods of a stack component don't resolve secret references."""
    secret_ref = "{{name.key}}"

    new_orchestrator = clean_client.create_stack_component(
        name="stub_orchestrator",
        component_type=StackComponentType.ORCHESTRATOR,
        configuration=StubOrchestratorConfig(
            attribute_without_validator=secret_ref,
        ).dict(),
        flavor="TEST",
    )
    assert (
        new_orchestrator.configuration["attribute_without_validator"]
        == secret_ref
    )
