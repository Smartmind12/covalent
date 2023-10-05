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

"""
Helper functions for the local executor
"""

import io
import json
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Callable, Dict, List, Tuple

import cloudpickle as pickle

from covalent._shared_files import logger
from covalent._workflow.depsbash import DepsBash
from covalent._workflow.depscall import RESERVED_RETVAL_KEY__FILES, DepsCall
from covalent._workflow.depspip import DepsPip
from covalent._workflow.transport import TransportableObject

app_log = logger.app_log


class AuthorizationError(Exception):
    pass


def wrapper_fn(
    function: TransportableObject,
    call_before: List[Tuple[TransportableObject, TransportableObject, TransportableObject]],
    call_after: List[Tuple[TransportableObject, TransportableObject, TransportableObject]],
    *args,
    **kwargs,
):
    """Wrapper for serialized callable.

    Execute preparatory shell commands before deserializing and
    running the callable. This is the actual function to be sent to
    the various executors.

    """
    cb_retvals = {}
    for tup in call_before:
        serialized_fn, serialized_args, serialized_kwargs, retval_key = tup
        cb_fn = serialized_fn.get_deserialized()
        cb_args = serialized_args.get_deserialized()
        cb_kwargs = serialized_kwargs.get_deserialized()
        retval = cb_fn(*cb_args, **cb_kwargs)

        # we always store cb_kwargs dict values as arrays to factor in non-unique values
        if retval_key and retval_key in cb_retvals:
            cb_retvals[retval_key].append(retval)
        elif retval_key:
            cb_retvals[retval_key] = [retval]

    # if cb_retvals key only contains one item this means it is a unique (non-repeated) retval key
    # so we only return the first element however if it is a 'files' kwarg we always return as a list
    cb_retvals = {
        key: value[0] if len(value) == 1 and key != RESERVED_RETVAL_KEY__FILES else value
        for key, value in cb_retvals.items()
    }

    fn = function.get_deserialized()

    new_args = [arg.get_deserialized() for arg in args]

    new_kwargs = {k: v.get_deserialized() for k, v in kwargs.items()}

    # Inject return values into kwargs
    for key, val in cb_retvals.items():
        new_kwargs[key] = val

    output = fn(*new_args, **new_kwargs)

    for tup in call_after:
        serialized_fn, serialized_args, serialized_kwargs, retval_key = tup
        ca_fn = serialized_fn.get_deserialized()
        ca_args = serialized_args.get_deserialized()
        ca_kwargs = serialized_kwargs.get_deserialized()
        ca_fn(*ca_args, **ca_kwargs)

    return TransportableObject(output)


def io_wrapper(fn: Callable, args: List, kwargs: Dict) -> Tuple[Any, str, str, str]:
    """Wrapper function to execute the given function in a separate
    process and capture stdout and stderr"""
    with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
        try:
            output = fn(*args, **kwargs)
            tb = ""
        except Exception as ex:
            output = None
            tb = "".join(traceback.TracebackException.from_exception(ex).format())
    return output, stdout.getvalue(), stderr.getvalue(), tb


# Copied from runner.py
def _gather_deps(deps, call_before_objs_json, call_after_objs_json) -> Tuple[List, List]:
    """Assemble deps for a node into the final call_before and call_after"""

    call_before = []
    call_after = []

    # Rehydrate deps from JSON
    if "bash" in deps:
        dep = DepsBash()
        dep.from_dict(deps["bash"])
        call_before.append(dep.apply())

    if "pip" in deps:
        dep = DepsPip()
        dep.from_dict(deps["pip"])
        call_before.append(dep.apply())

    for dep_json in call_before_objs_json:
        dep = DepsCall()
        dep.from_dict(dep_json)
        call_before.append(dep.apply())

    for dep_json in call_after_objs_json:
        dep = DepsCall()
        dep.from_dict(dep_json)
        call_after.append(dep.apply())

    return call_before, call_after


# Basic wrapper for executing a topologically sorted sequence of
# tasks. For the `task_specs` and `resources` schema see the comments
# for `AsyncBaseExecutor.send()`.


def get_node_asset(url: str) -> bytes:
    """Get node asset contents.

    Args:
        url: Request URL.

    """
    import requests

    headers = {"X-SESSION-TOKEN": os.getenv("COVALENT_JOB_SESSION_TOKEN")}

    if headers.get("X-SESSION-TOKEN") is None:
        raise AuthorizationError("Missing job session token")

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.content


def upload_node_asset(upload_url: str, asset_filepath: str) -> None:
    """Upload node asset contents.

    Args:
        upload_url: Request URL.
        asset_filepath: Path to asset file.

    """
    import requests

    headers = {"X-SESSION-TOKEN": os.getenv("COVALENT_JOB_SESSION_TOKEN")}

    if headers.get("X-SESSION-TOKEN") is None:
        raise AuthorizationError("Missing job session token")

    if asset_filepath:
        with open(asset_filepath, "rb") as f:
            requests.put(upload_url, data=f.read(), headers=headers)
        os.unlink(asset_filepath)
    sys.stdout.flush()


# URIs are just file paths
def run_task_from_uris(
    task_specs: List[Dict],
    resources: dict,
    output_uris: List[Tuple[str, str, str]],
    results_dir: str,
    task_group_metadata: dict,
    server_url: str,
):
    """Run task while using API calls to upload/download node asset contents.

    Args:
        task_specs: Task function, args and kwargs id.
        resources: Resources. Note: This variable is probably here to make this function adhere to some template, probably in parallel to the batch executor.
        output_uris: File paths for result, stdout and stderr.
        results_dir: Results directory.
        task_group_metadata: Task group metadata.
        server_url: Server URL.

    Raises:
        Exception if an error occurs during task execution or asset upload/download.

    """
    outputs = {}
    results = []
    dispatch_id = task_group_metadata["dispatch_id"]
    task_ids = task_group_metadata["task_ids"]
    gid = task_group_metadata["task_group_id"]

    os.environ["COVALENT_DISPATCH_ID"] = dispatch_id

    # For dev only -- log each task group
    app_log.debug(f"Running task group {dispatch_id}:{gid}")

    try:
        for i, task in enumerate(task_specs):
            result_uri, stdout_uri, stderr_uri = output_uris[i]

            with open(stdout_uri, "w") as stdout, open(stderr_uri, "w") as stderr:
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    try:
                        task_id = task["function_id"]
                        args_ids = task["args_ids"]
                        kwargs_ids = task["kwargs_ids"]

                        base_uri = f"{server_url}/api/v2/lattices/{dispatch_id}/assets/node"

                        import requests

                        serialized_fn = pickle.loads(
                            get_node_asset(url=f"{base_uri}/{task_id}/function/contents")
                        )

                        ser_args = [
                            pickle.loads(
                                get_node_asset(url=f"{base_uri}/{node_id}/output/contents")
                            )
                            for node_id in args_ids
                        ]

                        ser_kwargs = {
                            k: pickle.loads(
                                get_node_asset(url=f"{base_uri}/{node_id}/output/contents")
                            )
                            for k, node_id in kwargs_ids.items()
                        }

                        deps_json = pickle.loads(
                            get_node_asset(url=f"{base_uri}/{task_id}/deps/contents")
                        )

                        call_before_json = pickle.loads(
                            get_node_asset(url=f"{base_uri}/{task_id}/call_before/contents")
                        )

                        call_after_json = pickle.loads(
                            get_node_asset(url=f"{base_uri}/{task_id}/call_after/contents")
                        )

                        call_before, call_after = _gather_deps(
                            deps_json, call_before_json, call_after_json
                        )
                        exception_occurred = False

                        ser_output = wrapper_fn(
                            serialized_fn, call_before, call_after, *ser_args, **ser_kwargs
                        )

                        with open(result_uri, "wb") as f:
                            pickle.dump(ser_output, f)

                        outputs[task_id] = result_uri

                        result_summary = {
                            "node_id": task_id,
                            "output_uri": result_uri,
                            "stdout_uri": stdout_uri,
                            "stderr_uri": stderr_uri,
                            "exception_occurred": exception_occurred,
                        }
                        results.append(result_summary)

                    except Exception as ex:
                        exception_occurred = True
                        tb = "".join(traceback.TracebackException.from_exception(ex).format())
                        print(tb, file=sys.stderr)
                        result_uri = None
                        result_summary = {
                            "node_id": task_id,
                            "output_uri": result_uri,
                            "stdout_uri": stdout_uri,
                            "stderr_uri": stderr_uri,
                            "exception_occurred": exception_occurred,
                        }
                        results.append(result_summary)

                        break

                    finally:
                        upload_node_asset(
                            asset_filepath=result_uri,
                            upload_url=f"{base_uri}/{task_id}/output/contents",
                        )
                        upload_node_asset(
                            asset_filepath=stdout_uri,
                            upload_url=f"{base_uri}/{task_id}/stdout/contents",
                        )
                        upload_node_asset(
                            asset_filepath=stderr_uri,
                            upload_url=f"{base_uri}/{task_id}/stderr/contents",
                        )

                        result_path = os.path.join(
                            results_dir, f"result-{dispatch_id}:{task_id}.json"
                        )

                        with open(result_path, "w") as f:
                            json.dump(result_summary, f)

                        # Notify Covalent that the task has terminated
                        url = f"{server_url}/api/v1/update/{dispatch_id}/task/{task_id}"
                        response = requests.put(url)
                        response.raise_for_status()

        # Deal with any tasks that did not run
        n = len(results)
        if n < len(task_ids):
            for i in range(n, len(task_ids)):
                result_summary = {
                    "node_id": task_ids[i],
                    "output_uri": "",
                    "stdout_uri": "",
                    "stderr_uri": "",
                    "exception_occurred": True,
                }

                results.append(result_summary)

                result_path = os.path.join(results_dir, f"result-{dispatch_id}:{task_id}.json")

                with open(result_path, "w") as f:
                    json.dump(result_summary, f)

                url = f"{server_url}/api/v1/update/task/{dispatch_id}/{task_id}"
                response = requests.put(url)
                response.raise_for_status()

        # For debugging
        app_log.debug(f"Finished task group {dispatch_id}:{gid}")

    except Exception as ex:

        tb = "".join(traceback.TracebackException.from_exception(ex).format())
        app_log.error(f"Exception when running task group {dispatch_id}:{gid}")
        app_log.error(tb)

        raise ex
