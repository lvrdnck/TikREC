"""The service gate covers both accepted writers and new mutation attempts."""

from threading import Thread

import pytest

from tikrec.managed_gate import MutationGate


def test_two_writers_refuse_retention_without_stopping_work():
    gate = MutationGate()
    with gate.writer(), gate.writer():
        with pytest.raises(ValueError, match="active mutation"):
            with gate.exclusive():
                pytest.fail("occupied storage admitted retention")
    with gate.exclusive():
        gate.assert_exclusive()


def test_new_writer_and_second_retention_refuse_during_exclusion():
    gate = MutationGate()
    errors = []
    def mutate():
        try:
            with gate.writer():
                pytest.fail("writer entered exclusive retention")
        except ValueError as error:
            errors.append(error)
    with gate.exclusive():
        worker = Thread(target=mutate)
        worker.start()
        worker.join()
        with pytest.raises(ValueError):
            with gate.exclusive():
                pass
    assert len(errors) == 1
    with gate.writer():
        pass


def test_fault_releases_exclusion_and_writer_reservation():
    gate = MutationGate()
    with pytest.raises(KeyboardInterrupt):
        with gate.writer():
            raise KeyboardInterrupt
    with pytest.raises(OSError):
        with gate.exclusive():
            raise OSError("interrupted proof")
    with gate.writer():
        pass
    with pytest.raises(ValueError, match="not held"):
        gate.assert_exclusive()
