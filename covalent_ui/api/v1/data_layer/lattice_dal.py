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

"""Lattice Data Layer"""

from typing import List
from uuid import UUID

from sqlalchemy import extract, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import desc, func

from covalent_ui.api.v1.database.schema.lattices import Lattice
from covalent_ui.api.v1.models.dispatch_model import SortDirection
from covalent_ui.api.v1.models.lattices_model import LatticeDetail, LatticeDetailsFile


class Lattices:
    """Lattice data access layer"""

    def __init__(self, db_con: Session) -> None:
        self.db_con = db_con

    def get_lattices_id(self, dispatch_id: UUID) -> LatticeDetail:
        """
        Get lattices from dispatch id
        Args:
            dispatch_id: Refers to the dispatch_id in lattices table
        Return:
            Top most lattice with the given dispatch_id
            (i.e lattice with the same dispatch_id, but electron_id as null)
        """
        query = select(
            Lattice.dispatch_id,
            Lattice.status,
            Lattice.storage_path.label("directory"),
            Lattice.error_filename,
            Lattice.results_filename,
            Lattice.docstring_filename,
            Lattice.started_at.label("start_time"),
            func.coalesce((Lattice.completed_at), None).label("end_time"),
            Lattice.electron_num.label("total_electrons"),
            Lattice.completed_electron_num.label("total_electrons_completed"),
            (
                (
                    func.coalesce(
                        extract("epoch", Lattice.completed_at),
                        extract("epoch", func.now()),
                    )
                    - extract("epoch", Lattice.started_at)
                )
                * 1000
            ).label("runtime"),
            func.coalesce((Lattice.updated_at), None).label("updated_at"),
        ).where(Lattice.dispatch_id == str(dispatch_id), Lattice.is_active.is_not(False))
        lattice = self.db_con.execute(query).first()

        return lattice

    def get_lattices_id_storage_file(self, dispatch_id: UUID):
        """
        Get storage file name
        Args:
            dispatch_id: Refers to the dispatch_id in lattices table
        Return:
            Top most lattice with the given dispatch_id along with file names
            (i.e lattice with the same dispatch_id, but electron_id as null)
        """

        query = select(
            Lattice.dispatch_id,
            Lattice.status,
            Lattice.storage_path.label("directory"),
            Lattice.error_filename,
            Lattice.function_string_filename,
            Lattice.executor,
            Lattice.executor_data_filename,
            Lattice.workflow_executor,
            Lattice.workflow_executor_data_filename,
            Lattice.error_filename,
            Lattice.inputs_filename,
            Lattice.results_filename,
            Lattice.storage_type,
            Lattice.function_filename,
            Lattice.transport_graph_filename,
            Lattice.started_at.label("started_at"),
            Lattice.completed_at.label("ended_at"),
            Lattice.electron_num.label("total_electrons"),
            Lattice.completed_electron_num.label("total_electrons_completed"),
        ).where(Lattice.dispatch_id == str(dispatch_id), Lattice.is_active.is_not(False))
        lattice = self.db_con.execute(query).first()
        return LatticeDetailsFile.model_validate(lattice) if lattice is not None else None

    # def get_lattice_id_by_dispatch_id(self, dispatch_id: UUID):
    #     """
    #     Get top lattice id from dispatch id
    #     Args:
    #         dispatch_id: UUID of dispatch
    #     Returns:
    #         Top most lattice id
    #     """
    #     data = (
    #         self.db_con.query(Lattice.id)
    #         .filter(Lattice.dispatch_id == str(dispatch_id), Lattice.electron_id.is_(None))
    #         .first()
    #     )
    #     return data[0]

    def get_sub_lattice_details(self, sort_by, sort_direction, dispatch_id) -> List[Lattice]:
        """
        Get summary of sub lattices
        Args:
            req.sort_by: sort by field name(run_time, status, lattice_name)
            req.direction: sort by direction ASE, DESC
        Return:
            List of sub Lattices
        """
        query = (
            select(
                Lattice.dispatch_id.label("dispatch_id"),
                Lattice.name.label("lattice_name"),
                (
                    (
                        func.coalesce(
                            extract("epoch", Lattice.completed_at), extract("epoch", func.now())
                        )
                        - extract("epoch", Lattice.started_at)
                    )
                    * 1000
                ).label("runtime"),
                Lattice.electron_num.label("total_electrons"),
                Lattice.completed_electron_num.label("total_electrons_completed"),
                Lattice.status.label("status"),
                Lattice.started_at.label("started_at"),
                func.coalesce((Lattice.completed_at), None).label("ended_at"),
                Lattice.updated_at.label("updated_at"),
            )
            .filter(
                Lattice.is_active.is_not(False),
                Lattice.electron_id.is_not(None),
                Lattice.root_dispatch_id == str(dispatch_id),
            )
            .order_by(
                desc(sort_by.value)
                if sort_direction == SortDirection.DESCENDING
                else sort_by.value
            )
        )

        data = self.db_con.execute(query).all()

        return data
