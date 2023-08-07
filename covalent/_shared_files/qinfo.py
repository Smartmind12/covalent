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

"""QNode and QElectron information containers."""

from typing import Any, Dict, Optional, Sequence, Union

from pydantic import BaseModel  # pylint: disable=no-name-in-module


class QNodeSpecs(BaseModel):
    """
    A container for the specifications of a QNode.
    """
    gate_sizes: Dict[str, int]
    gate_types: Dict[str, int]
    num_operations: int
    num_observables: int
    num_diagonalizing_gates: int
    num_used_wires: int
    depth: int
    num_trainable_params: int = None
    num_device_wires: int
    device_name: str
    diff_method: Optional[str]
    expansion_strategy: str
    gradient_options: Dict[str, int]
    interface: Optional[str]
    gradient_fn: Optional[str]
    num_gradient_executions: Any = 0
    num_parameter_shift_executions: int = None


class QElectronInfo(BaseModel):
    """
    A container for related settings used by the wrapping QElectron.
    """
    name: str
    description: str = None
    device_name: str  # name of the original device, e.g. "default.qubit"
    device_import_path: str  # used to inherit type converters and other methods
    device_shots: Union[None, int, Sequence[int], Sequence[Union[int, Sequence[int]]]]  # optional default for execution devices
    device_shots_type: Any = None
    device_wires: int  # this can not be reliably inferred from tapes alone
    pennylane_active_return: bool  # client-side status of `pennylane.active_return()`
