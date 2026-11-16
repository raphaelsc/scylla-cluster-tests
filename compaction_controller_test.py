#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright (c) 2026 ScyllaDB

from longevity_test import LongevityTest
from sdcm.sct_events.system import InfoEvent


class CompactionControllerTest(LongevityTest):
    """Compaction controller workloads that the longevity flow can't express."""

    def test_write_read_cycles(self):
        """Alternate a write phase and a read phase.

        The longevity flow starts every stress command at once. Here, for each i in order,
        stress_cmd[i] runs to completion, then stress_read_cmd[i] runs to completion: a cycle
        is one entry of each list, and both lists must be as long. Each entry is one command.
        prepare_write_cmd, if set, runs once before the first cycle.
        """
        writes = self._as_list(self.params.get("stress_cmd"))
        reads = self._as_list(self.params.get("stress_read_cmd"))
        assert writes and len(writes) == len(reads), (
            f"stress_cmd and stress_read_cmd must have the same number of entries, one per cycle: "
            f"{len(writes)} and {len(reads)}"
        )
        self.db_cluster.add_nemesis(nemesis=self.get_nemesis_class(), tester_obj=self)
        self.run_pre_create_keyspace()
        self.run_pre_create_schema()
        self.run_prepare_write_cmd()
        for cycle, (write_cmd, read_cmd) in enumerate(zip(writes, reads), start=1):
            for phase, cmd in (("write", write_cmd), ("read", read_cmd)):
                InfoEvent(message=f"Cycle {cycle} of {len(writes)}: {phase} phase starts").publish()
                queue = []
                self._run_all_stress_cmds(queue, {"stress_cmd": [cmd], "round_robin": self.params.get("round_robin")})
                for stress in queue:
                    self.verify_stress_thread(stress)

    @staticmethod
    def _as_list(cmds):
        if not cmds:
            return []
        return [cmds] if isinstance(cmds, str) else list(cmds)
