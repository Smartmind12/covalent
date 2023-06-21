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

import pennylane as qml

from ..middleware.core import middleware


class QNodeFutureResult:

    def __init__(self, batch_id, dummy_result):
        self.batch_id = batch_id
        self.dummy_result = dummy_result

        self._result = None

    def result(self):
        """
        Retrieve the results from middleware for the given batch_id.

        Returns:
            Any: The results of the circuit execution.
        """

        if self._result is not None:
            return self._result

        results = middleware.get_results(self.batch_id)

        self._result = qml.math.convert_like(results[0], self.dummy_result)
        return self._result
