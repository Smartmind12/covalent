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


"""Unit tests for local module in dispatcher_plugins."""


import covalent as ct
from covalent._dispatcher_plugins.local import get_redispatch_request_body


def test_get_redispatch_request_body_null_arguments():
    """Test the get request body function with null arguments."""

    @ct.electron
    def identity(a):
        return a

    @ct.electron
    def add(a, b):
        return a + b

    response = get_redispatch_request_body(
        "mock-dispatch-id",
    )
    assert response == {
        "json_lattice": None,
        "dispatch_id": "mock-dispatch-id",
        "electron_updates": {},
        "reuse_previous_results": False,
    }
