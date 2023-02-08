import contextlib

from zenml.pipelines import BasePipeline
from zenml.steps import step


class _DynamicPipeline(BasePipeline):
    def connect(self, *args, **kwargs) -> None:
        pass


@contextlib.contextmanager
def pipeline(name: str) -> ...:
    pipeline_class = type(name, (_DynamicPipeline,), {})
    pipeline_instance = pipeline_class()
    BasePipeline._ACTIVE_PIPELINE = pipeline_instance
    yield pipeline_instance
    BasePipeline._ACTIVE_PIPELINE = None


@step
def s1() -> int:
    return 1


@step
def s2(a: int) -> None:
    pass


with pipeline(name="test") as p:
    out = s1()
    for _ in range(10):
        s1()
    s2(out)


p.run(enable_cache=False, unlisted=True)
