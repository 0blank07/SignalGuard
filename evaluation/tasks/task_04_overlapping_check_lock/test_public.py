import pytest
from target import ExecutionCoordinator


def test_public_acquire_and_release():
    coord = ExecutionCoordinator()
    assert coord.acquire(1) is True
    coord.release(1)
