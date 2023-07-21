# Copyright 2023 Agnostiq Inc.
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

import base64
from typing import Callable, Union

from ..shared_utils import cloudpickle_deserialize, cloudpickle_serialize
from .base import AsyncBaseQCluster
from .default_selectors import selector_map

__all__ = [
    "QCluster",
]


class QCluster(AsyncBaseQCluster):
    """
    A class that abstracts a collection of individual quantum executors and provides
    a custom selection algorithm for choosing executors on a per-qscript basis.

    Args:
        executors: The list (or sequence) of quantum executors comprising the
            cluster.
        selector: A callable that selects an executor. The strings "cyclic" and
            "random" are also accepted. The default "cyclic" selector returns
            elements of `executors` in order, restarting from the first element
            upon reaching the last. The "random" selector chooses from `executors`
            at random, for each circuit. Any user-defined selector must be callable
            with two arguments (a circuit and a list of executors), and must always
            return only one executor.
    """

    selector: Union[str, Callable] = "cyclic"

    # Flag used to indicate whether `self.selector` is currently serialized.
    _selector_serialized: bool = False

    def batch_submit(self, qscripts_list):
        if self._selector_serialized:
            self.selector = self.deserialize_selector()

        selector = self.get_selector()
        selected_executor = selector(qscripts_list, self.executors)

        # copy server-side set attributes into selector executor
        selected_executor.qnode_device_import_path = self.qnode_device_import_path
        selected_executor.qnode_device_shots = self.qnode_device_shots
        selected_executor.qnode_device_wires = self.qnode_device_wires
        selected_executor.pennylane_active_return = self.pennylane_active_return
        return selected_executor.batch_submit(qscripts_list)

    def serialize_selector(self) -> None:
        if self._selector_serialized:
            return

        # serialize to bytes with cloudpickle
        self.selector = cloudpickle_serialize(self.selector)

        # convert to string to make JSON-able
        self.selector = base64.b64encode(self.selector).decode("utf-8")
        self._selector_serialized = True

    def deserialize_selector(self) -> Union[str, Callable]:
        if not self._selector_serialized:
            return self.selector

        # Deserialize the selector function (or string).
        selector = cloudpickle_deserialize(
            base64.b64decode(self.selector.encode("utf-8"))
        )

        self._selector_serialized = False
        return selector

    def dict(self, *args, **kwargs) -> dict:
        # override `dict` method to convert dict attributes to JSON strings
        dict_ = super(AsyncBaseQCluster, self).dict(*args, **kwargs)
        dict_.update(executors=tuple(ex.json() for ex in self.executors))
        return dict_

    def get_selector(self) -> Callable:
        """
        Wraps `self.selector` to return defaults corresponding to string values.

        This method is called inside `batch_submit`.
        """
        self.selector = self.deserialize_selector()

        if isinstance(self.selector, str):
            # use default selector
            selector_cls = selector_map[self.selector]
            self.selector = selector_cls()

        return self.selector
