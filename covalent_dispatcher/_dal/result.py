# Copyright 2021 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the GNU Affero General Public License 3.0 (the "License").
# A copy of the License may be obtained with this software package or at
#
#      https://www.gnu.org/licenses/agpl-3.0.en.html
#
# Use of this file is prohibited except in compliance with the License. Any
# modifications or derivative works of this file must retain this copyright
# notice, and modified files must contain a notice indicating that they have
# been altered from the originals.
#
# Covalent is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the License for more details.
#
# Relief from the License may be granted by purchasing a commercial license.

"""DB-backed lattice"""

import os
from datetime import datetime
from typing import Any, List

from sqlalchemy.orm import Session

from covalent._shared_files import logger
from covalent._shared_files.defaults import postprocess_prefix
from covalent._shared_files.util_classes import RESULT_STATUS, Status

from .._db import models
from .asset import Asset
from .base import DispatchedObject
from .controller import Record
from .db_interfaces.result_utils import ASSET_KEYS  # nopycln: import
from .db_interfaces.result_utils import METADATA_KEYS  # nopycln: import
from .db_interfaces.result_utils import _meta_record_map, get_filters, set_filters
from .electron import ELECTRON_KEYS
from .lattice import LATTICE_KEYS, Lattice

app_log = logger.app_log

RESULT_KEYS = list(_meta_record_map.keys())


class ResultMeta(Record):
    model = models.Lattice


class ResultAsset(Record):
    model = models.LatticeAsset


class Result(DispatchedObject):
    meta_type = ResultMeta
    asset_link_type = ResultAsset
    metadata_keys = RESULT_KEYS

    def __init__(
        self,
        session: Session,
        record: models.Lattice,
        bare: bool = False,
        *,
        keys: list = RESULT_KEYS,
        lattice_keys: list = LATTICE_KEYS,
        electron_keys: list = ELECTRON_KEYS,
    ):
        self._id = record.id
        self._keys = keys
        fields = set(map(Result.meta_record_map, keys))
        self._metadata = ResultMeta(session, record, fields=fields)
        self._assets = {}

        self._lattice_id = record.id
        self._electron_id = record.electron_id

        self.lattice = Lattice(
            session, record, bare, keys=lattice_keys, electron_keys=electron_keys
        )

        self._task_failed = False
        self._task_cancelled = False

        # For lattice updates
        self._start_time = None
        self._end_time = None
        self._status = None
        self._error = None
        self._result = None

    @property
    def query_keys(self) -> List:
        return self._keys

    @property
    def metadata(self) -> ResultMeta:
        return self._metadata

    @property
    def assets(self):
        return self._assets

    @classmethod
    def meta_record_map(cls: DispatchedObject, key: str) -> str:
        return _meta_record_map[key]

    @property
    def start_time(self):
        return self.get_metadata("start_time")

    @property
    def end_time(self):
        return self.get_metadata("end_time")

    @property
    def dispatch_id(self):
        return self.get_metadata("dispatch_id")

    @property
    def root_dispatch_id(self):
        return self.get_metadata("root_dispatch_id")

    @property
    def status(self) -> Status:
        return Status(self.get_metadata("status"))

    @property
    def result(self):
        return self.get_asset("result").load_data()

    @property
    def error(self):
        return self.get_asset("error").load_data()

    def commit(self):
        with self.session() as session:
            if self._start_time is not None:
                self.set_value("start_time", self._start_time, session)
                self._start_time = None

            if self._end_time is not None:
                self.set_value("end_time", self._end_time, session)
                self._end_time = None

            if self._status is not None:
                self.set_value("status", str(self._status), session)
                self._status = None

            if self._error is not None:
                self.set_value("error", self._error, session)
                self._error = None

            if self._result is not None:
                self.set_value("result", self._result, session)
                self._result = None

    def get_value(self, key: str, session: Session = None, refresh: bool = True):
        return get_filters[key](super().get_value(key, session, refresh))

    def set_value(self, key: str, val: Any, session: Session = None) -> None:
        super().set_value(key, set_filters[key](val), session)

    def _update_dispatch(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        status: "Status" = None,
        error: str = None,
        result: Any = None,
    ):
        with self.session() as session:
            if start_time is not None:
                self.set_value("start_time", start_time, session)
            if end_time is not None:
                self.set_value("end_time", end_time, session)
            if status is not None:
                self.set_value("status", status, session)
            if error is not None:
                self.set_value("error", error, session)
            if result is not None:
                self.set_value("result", result, session)

    def _update_node(
        self,
        node_id: int,
        node_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        status: "Status" = None,
        output: Any = None,
        error: Exception = None,
        stdout: str = None,
        stderr: str = None,
        output_uri: str = None,
        stdout_uri: str = None,
        stderr_uri: str = None,
    ) -> None:
        """
        Update the node result in the transport graph.
        Called after any change in node's execution state.

        Args:
            node_id: The node id.
            node_name: The name of the node.
            start_time: The start time of the node execution.
            end_time: The end time of the node execution.
            status: The status of the node execution.
            output: The output of the node unless error occured in which case None.
            error: The error of the node if occured else None.
            stdout: The stdout of the node execution.
            stderr: The stderr of the node execution.

        Returns:
            None
        """

        app_log.debug("Inside update node")

        with self.session() as session:
            # Current node name
            name = self.lattice.transport_graph.get_node_value(node_id, "name", session)

            if node_name is not None:
                self.lattice.transport_graph.set_node_value(node_id, "name", node_name, session)

            if start_time is not None:
                self.lattice.transport_graph.set_node_value(
                    node_id, "start_time", start_time, session
                )

            if end_time is not None:
                self.lattice.transport_graph.set_node_value(node_id, "end_time", end_time, session)

            if status is not None:
                self.lattice.transport_graph.set_node_value(node_id, "status", status, session)
                if status == RESULT_STATUS.COMPLETED:
                    completed_num = self.get_value("completed_electron_num", session)
                    self.set_value("completed_electron_num", completed_num + 1, session)

            if output is not None:
                self.lattice.transport_graph.set_node_value(node_id, "output", output, session)

            if error is not None:
                self.lattice.transport_graph.set_node_value(node_id, "error", error, session)

            if stdout is not None:
                self.lattice.transport_graph.set_node_value(node_id, "stdout", stdout, session)

            if stderr is not None:
                self.lattice.transport_graph.set_node_value(node_id, "stderr", stderr, session)

        # Handle postprocessing node
        tg = self.lattice.transport_graph
        if name.startswith(postprocess_prefix) and end_time is not None:
            workflow_result = self.get_asset("result")
            node_output = tg.get_node(node_id).get_asset("output")
            _copy_asset(node_output, workflow_result)
            self._status = status
            self._end_time = end_time
            app_log.debug(f"Postprocess status: {self._status}")
            self.commit()

    def _get_failed_nodes(self) -> List[int]:
        """
        Get the node_id of each failed task
        """
        return self._get_incomplete_nodes()["failed"]

    def _get_incomplete_nodes(self, refresh: bool = True):
        nodes = []
        num_nodes = self.get_metadata("num_nodes")
        tg = self.lattice.transport_graph

        with self.session() as session:
            failed_nodes = [
                (i, tg.get_node_value(i, "name", session, refresh))
                for i in range(num_nodes)
                if tg.get_node_value(i, "status", session, refresh) == RESULT_STATUS.FAILED
            ]
            cancelled_nodes = [
                (i, tg.get_node_value(i, "name", session, refresh))
                for i in range(num_nodes)
                if tg.get_node_value(i, "status", session, refresh) == RESULT_STATUS.CANCELLED
            ]
        return {"failed": failed_nodes, "cancelled": cancelled_nodes}

    def get_all_node_outputs(self) -> dict:
        """
        Return output of every node execution.

        Args:
            None

        Returns:
            node_outputs: A dictionary containing the output of every node execution.
        """

        all_node_outputs = {}
        tg = self.lattice.transport_graph
        for node_id in tg._graph.nodes:
            node_name = tg.get_node_value(node_id, "name")
            node_output = tg.get_node_value(node_id, "output")
            all_node_outputs[f"{node_name}({node_id})"] = node_output
        return all_node_outputs


def _copy_asset(src: Asset, dest: Asset):
    scheme = dest.storage_type.value
    dest_uri = scheme + "://" + os.path.join(dest.storage_path, dest.object_key)
    src.upload(dest_uri)


def get_result_object(
    dispatch_id: str,
    bare: bool = False,
    *,
    keys: list = RESULT_KEYS,
    lattice_keys: list = LATTICE_KEYS,
    electron_keys: list = ELECTRON_KEYS,
) -> Result:
    with Result.session() as session:
        records = Result.get_db_records(
            session,
            keys=keys + lattice_keys,
            equality_filters={"dispatch_id": dispatch_id},
            membership_filters={},
        )
        if not records:
            raise KeyError(f"Dispatch {dispatch_id} not found")

        record = records[0]

        return Result(
            session,
            record,
            bare,
            keys=keys,
            lattice_keys=lattice_keys,
            electron_keys=electron_keys,
        )
