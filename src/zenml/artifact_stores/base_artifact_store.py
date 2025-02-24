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
"""The base interface to extend the ZenML artifact store."""
import textwrap
from abc import abstractmethod
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic import root_validator

from zenml.enums import StackComponentType
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stack import Flavor, StackComponent, StackComponentConfig
from zenml.utils import io_utils

logger = get_logger(__name__)

PathType = Union[bytes, str]


def _sanitize_potential_path(potential_path: Any) -> Any:
    """Sanitizes the input if it is a path.

    If the input is a **remote** path, this function replaces backslash path
    separators by forward slashes.

    Args:
        potential_path: Value that potentially refers to a (remote) path.

    Returns:
        The original input or a sanitized version of it in case of a remote
        path.
    """
    if isinstance(potential_path, bytes):
        path = fileio.convert_to_str(potential_path)
    elif isinstance(potential_path, str):
        path = potential_path
    else:
        # Neither string nor bytes, this is not a path
        return potential_path

    if io_utils.is_remote(path):
        # If we have a remote path, replace windows path separators with
        # slashes
        import ntpath
        import posixpath

        path = path.replace(ntpath.sep, posixpath.sep)

    return path


def _sanitize_paths(_func: Callable[..., Any]) -> Callable[..., Any]:
    """Sanitizes path inputs before calling the original function.

    Args:
        _func: The function for which to sanitize the inputs.

    Returns:
        Function that calls the input function with sanitized path inputs.
    """

    def inner_function(*args: Any, **kwargs: Any) -> Any:
        """Inner function.

        Args:
            *args: Positional args.
            **kwargs: Keyword args.

        Returns:
            Output of the input function called with sanitized paths.
        """
        args = tuple(_sanitize_potential_path(arg) for arg in args)
        kwargs = {
            key: _sanitize_potential_path(value)
            for key, value in kwargs.items()
        }

        return _func(*args, **kwargs)

    return inner_function


class BaseArtifactStoreConfig(StackComponentConfig):
    """Config class for `BaseArtifactStore`."""

    path: str

    SUPPORTED_SCHEMES: ClassVar[Set[str]]

    @root_validator(skip_on_failure=True)
    def _ensure_artifact_store(cls, values: Dict[str, Any]) -> Any:
        """Validator function for the Artifact Stores.

        Checks whether supported schemes are defined and the given path is
        supported.

        Args:
            values: The values to validate.

        Returns:
            The validated values.

        Raises:
            ArtifactStoreInterfaceError: If the scheme is not supported.
        """
        try:
            getattr(cls, "SUPPORTED_SCHEMES")
        except AttributeError:
            raise ArtifactStoreInterfaceError(
                textwrap.dedent(
                    """
                    When you are working with any classes which subclass from
                    zenml.artifact_store.BaseArtifactStore please make sure
                    that your class has a ClassVar named `SUPPORTED_SCHEMES`
                    which should hold a set of supported file schemes such
                    as {"s3://"} or {"gcs://"}.

                    Example:

                    class MyArtifactStoreConfig(BaseArtifactStoreConfig):
                        ...
                        # Class Variables
                        SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"s3://"}
                        ...
                    """
                )
            )
        if not any(
            values["path"].startswith(i) for i in cls.SUPPORTED_SCHEMES
        ):
            raise ArtifactStoreInterfaceError(
                f"The path: '{values['path']}' you defined for your "
                f"artifact store is not supported by the implementation of "
                f"{cls.schema()['title']}, because it does not start with "
                f"one of its supported schemes: {cls.SUPPORTED_SCHEMES}."
            )

        return values


class BaseArtifactStore(StackComponent):
    """Base class for all ZenML artifact stores."""

    @property
    def config(self) -> BaseArtifactStoreConfig:
        """Returns the `BaseArtifactStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseArtifactStoreConfig, self._config)

    @property
    def path(self) -> str:
        """The path to the artifact store.

        Returns:
            The path.
        """
        return self.config.path

    # --- User interface ---
    @abstractmethod
    def open(self, name: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            name: The path of the file to open.
            mode: The mode to open the file.

        Returns:
            The file object.
        """

    @abstractmethod
    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file from the source to the destination.

        Args:
            src: The source path.
            dst: The destination path.
            overwrite: Whether to overwrite the destination file if it exists.
        """

    @abstractmethod
    def exists(self, path: PathType) -> bool:
        """Checks if a path exists.

        Args:
            path: The path to check.

        Returns:
            `True` if the path exists.
        """

    @abstractmethod
    def glob(self, pattern: PathType) -> List[PathType]:
        """Gets the paths that match a glob pattern.

        Args:
            pattern: The glob pattern.

        Returns:
            The list of paths that match the pattern.
        """

    @abstractmethod
    def isdir(self, path: PathType) -> bool:
        """Returns whether the given path points to a directory.

        Args:
            path: The path to check.

        Returns:
            `True` if the path points to a directory.
        """

    @abstractmethod
    def listdir(self, path: PathType) -> List[PathType]:
        """Returns a list of files under a given directory in the filesystem.

        Args:
            path: The path to list.

        Returns:
            The list of files under the given path.
        """

    @abstractmethod
    def makedirs(self, path: PathType) -> None:
        """Make a directory at the given path, recursively creating parents.

        Args:
            path: The path to create.
        """

    @abstractmethod
    def mkdir(self, path: PathType) -> None:
        """Make a directory at the given path; parent directory must exist.

        Args:
            path: The path to create.
        """

    @abstractmethod
    def remove(self, path: PathType) -> None:
        """Remove the file at the given path. Dangerous operation.

        Args:
            path: The path to remove.
        """

    @abstractmethod
    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename source file to destination file.

        Args:
            src: The source path.
            dst: The destination path.
            overwrite: Whether to overwrite the destination file if it exists.
        """

    @abstractmethod
    def rmtree(self, path: PathType) -> None:
        """Deletes dir recursively. Dangerous operation.

        Args:
            path: The path to delete.
        """

    @abstractmethod
    def stat(self, path: PathType) -> Any:
        """Return the stat descriptor for a given file path.

        Args:
            path: The path to check.

        Returns:
            The stat descriptor.
        """

    def size(self, path: PathType) -> Optional[int]:
        """Get the size of a file in bytes.

        Args:
            path: The path to the file.

        Returns:
            The size of the file in bytes or `None` if the artifact store
            does not implement the `size` method.
        """
        logger.warning(
            "Cannot get size of file '%s' since the artifact store %s does not "
            "implement the `size` method.",
            path,
            self.__class__.__name__,
        )
        return None

    @abstractmethod
    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory.

        Args:
            top: The path to walk.
            topdown: Whether to walk the top-down or bottom-up.
            onerror: The error handler.

        Returns:
            The iterator that walks the contents of the given directory.
        """

    # --- Internal interface ---
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initiate the Pydantic object and register the corresponding filesystem.

        Args:
            *args: The positional arguments to pass to the Pydantic object.
            **kwargs: The keyword arguments to pass to the Pydantic object.
        """
        super(BaseArtifactStore, self).__init__(*args, **kwargs)
        self._register()

    def _register(self) -> None:
        """Create and register a filesystem within the filesystem registry."""
        from zenml.io.filesystem import BaseFilesystem
        from zenml.io.filesystem_registry import default_filesystem_registry
        from zenml.io.local_filesystem import LocalFilesystem

        # Local filesystem is always registered, no point in doing it again.
        if isinstance(self, LocalFilesystem):
            return

        filesystem_class = type(
            self.__class__.__name__,
            (BaseFilesystem,),
            {
                "SUPPORTED_SCHEMES": self.config.SUPPORTED_SCHEMES,
                "open": staticmethod(_sanitize_paths(self.open)),
                "copyfile": staticmethod(_sanitize_paths(self.copyfile)),
                "exists": staticmethod(_sanitize_paths(self.exists)),
                "glob": staticmethod(_sanitize_paths(self.glob)),
                "isdir": staticmethod(_sanitize_paths(self.isdir)),
                "listdir": staticmethod(_sanitize_paths(self.listdir)),
                "makedirs": staticmethod(_sanitize_paths(self.makedirs)),
                "mkdir": staticmethod(_sanitize_paths(self.mkdir)),
                "remove": staticmethod(_sanitize_paths(self.remove)),
                "rename": staticmethod(_sanitize_paths(self.rename)),
                "rmtree": staticmethod(_sanitize_paths(self.rmtree)),
                "size": staticmethod(_sanitize_paths(self.size)),
                "stat": staticmethod(_sanitize_paths(self.stat)),
                "walk": staticmethod(_sanitize_paths(self.walk)),
            },
        )

        default_filesystem_registry.register(filesystem_class)


class BaseArtifactStoreFlavor(Flavor):
    """Base class for artifact store flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.ARTIFACT_STORE

    @property
    def config_class(self) -> Type[StackComponentConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return BaseArtifactStoreConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseArtifactStore"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
