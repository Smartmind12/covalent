"""Pennylane-Qiskit devices to Quantum Electrons"""
from typing import Any, List, Tuple, Union

from pennylane import active_return
from qiskit.primitives import Sampler as LocalSampler
from qiskit_ibm_runtime import Sampler

from .utils import extract_options
from .wrappers import _LocalQiskitDevice, _QiskitRuntimeDevice, _SamplerDevice


class QiskitLocalSampler(_LocalQiskitDevice, _SamplerDevice):
    """
    Pennylane device that runs circuits using the local `qiskit.primitives.Sampler`
    """

    short_name = "local_sampler"

    def __init__(self, wires: int, shots: int, **_):

        _LocalQiskitDevice.__init__(self)
        _SamplerDevice.__init__(
            self,
            wires=wires,
            shots=shots,
            backend_name="None",
            service_init_kwargs={},
        )

    def batch_execute(self, circuits):
        jobs = []
        sampler = LocalSampler()
        for circuit in circuits:
            tapes = self.broadcast_tapes([circuit])
            compiled_circuits = self.compile_circuits(tapes)  # NOTE: slow step
            job = sampler.run(compiled_circuits)
            jobs.append(job)

        return [[job.result()] for job in jobs]


class QiskitRuntimeSampler(_QiskitRuntimeDevice, _SamplerDevice):
    """
    Pennylane device that runs circuits with Qiskit Runtime's `Sampler`
    """

    short_name = "sampler"

    def __init__(
        self,
        wires: int,
        shots: int,
        backend_name: str,
        max_time: Union[int, str],
        options: dict,
        service_init_kwargs: dict,
    ):

        _options = extract_options(options)
        _options.execution.shots = shots
        self.options = _options
        self.max_time = max_time

        _SamplerDevice.__init__(
            self,
            wires=wires,
            shots=shots,
            backend_name=backend_name,
            service_init_kwargs=service_init_kwargs,
        )

    def batch_execute(self, circuits):

        with super().session(  # pylint: disable=not-context-manager
            self.service,
            self.backend,
            self.max_time
        ) as session:

            sampler = Sampler(session=session, options=self.options)
            jobs = []
            for circuit in circuits:
                tapes = self.broadcast_tapes([circuit])
                compiled_circuits = self.compile_circuits(tapes)  # NOTE: slow step
                job = sampler.run(compiled_circuits)
                jobs.append(job)

        if not active_return():
            jobs = [[job] for job in jobs]

        return jobs

    def post_process(self, qscripts_list, results) -> Tuple[List[Any], List[dict]]:
        results = [[self.request_result(job)] for job in results]
        return _SamplerDevice.post_process(self, qscripts_list, results)
