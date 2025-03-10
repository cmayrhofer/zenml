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
"""Tekton orchestrator flavor."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pydantic import root_validator

from zenml.integrations.tekton import TEKTON_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.tekton.orchestrators import TektonOrchestrator

from zenml.config.base_settings import BaseSettings
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.logger import get_logger

logger = get_logger(__name__)


class TektonOrchestratorSettings(BaseSettings):
    """Settings for the Tekton orchestrator.

    Attributes:
        pod_settings: Pod settings to apply.
    """

    pod_settings: Optional[KubernetesPodSettings] = None


class TektonOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseOrchestratorConfig, TektonOrchestratorSettings
):
    """Configuration for the Tekton orchestrator.

    Attributes:
        kubernetes_context: Name of a kubernetes context to run
            pipelines in.
        kubernetes_namespace: Name of the kubernetes namespace in which the
            pods that run the pipeline steps should be running.
        local: If `True`, the orchestrator will assume it is connected to a
            local kubernetes cluster and will perform additional validations and
            operations to allow using the orchestrator in combination with other
            local stack components that store data in the local filesystem
            (i.e. it will mount the local stores directory into the pipeline
            containers).
        skip_local_validations: If `True`, the local validations will be
            skipped.
    """

    kubernetes_context: str  # TODO: Potential setting
    kubernetes_namespace: str = "zenml"
    local: bool = False
    skip_local_validations: bool = False

    @root_validator(pre=True)
    def _validate_deprecated_attrs(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pydantic root_validator for deprecated attributes.

        This root validator is used for backwards compatibility purposes. E.g.
        it handles attributes that are no longer available or that have become
        mandatory in the meantime.

        Args:
            values: Values passed to the object constructor

        Returns:
            Values passed to the object constructor

        """
        provisioning_attrs = [
            "tekton_ui_port",
            "skip_ui_daemon_provisioning",
        ]

        provisioning_attrs_used = [
            attr for attr in provisioning_attrs if attr in values
        ]

        msg_header = (
            "Automatically exposing the Tekton UI TCP port locally as part of "
            "the stack provisioning using `zenml stack up` has been "
            "removed in favor of methods better suited for this "
            "purpose, such as using an Ingress controller in the remote "
            "cluster. \n"
            "As a result, the following Kubernetes orchestrator configuration "
            "attributes have been deprecated: "
            f"{provisioning_attrs}.\n"
        )

        if provisioning_attrs_used:
            logger.warning(
                msg_header
                + "To get rid of this warning, you should remove the deprecated "
                "attributes from your orchestrator configuration (e.g. by "
                "using the `zenml orchestrator remove-attribute <attr-name>` "
                "CLI command)."
            )
            # remove deprecated attributes from values dict
            for attr in provisioning_attrs_used:
                del values[attr]

        return values

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return not self.local

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return self.local


class TektonOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Tekton orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return TEKTON_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[TektonOrchestratorConfig]:
        """Returns `TektonOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return TektonOrchestratorConfig

    @property
    def implementation_class(self) -> Type["TektonOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.tekton.orchestrators import TektonOrchestrator

        return TektonOrchestrator
