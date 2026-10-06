"""Direct helpers, reentrant calls and foreign threads cannot replace live recovery."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.journal_assembly_helpers import managed_process
from tests.test_release_recovery_cleanup import recovery_case
from tikrec.release_recovery import recover_prepared_release
from tikrec.session_journal_types import JournalError


def test_direct_helper_reentrancy_and_foreign_reader_are_refused(recovery_case):
    owner, case = recovery_case
    before = owner.journal.path.read_bytes()
    with pytest.raises(JournalError, match='execution fence'):
        recover_prepared_release(owner, case['session'], case['token'])
    assert owner.journal.path.read_bytes() == before and not owner._recovery_owners
    def fault(point):
        if point == 'after_recovery_authority':
            active = owner._release_recovery
            with pytest.raises(JournalError, match='another recovery execution'):
                owner.recover_prepared_release(case['session'], case['token'])
            assert owner._release_recovery is active
            with ThreadPoolExecutor(max_workers=1) as pool:
                read = pool.submit(active.view.session, case['session'])
                with pytest.raises(JournalError, match='reader scope'):
                    read.result(timeout=2)
            assert owner._recovery_owners[case['token']] is active
    assert owner.recover_prepared_release(case['session'], case['token'], fault=fault)['state'] == 'released'
    assert owner.journal.release_recovery(case['token'])['head']['generation'] == 1
    assert owner.journal.status()['units'] == [] and not owner._recovery_owners
