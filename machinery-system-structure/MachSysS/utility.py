
__all__ = ["retrieve_machinery_system_from_file", "retrieve_gymir_result_from_file"]

# %% ../02_Utility.ipynb 3
import io
from typing import Union

import MachSysS.gymir_result_pb2 as proto_gymir
import MachSysS.system_structure_pb2 as proto_system


def retrieve_machinery_system_from_file(
    file: Union[str, io.BytesIO],
) -> proto_system.MachinerySystem:
    if isinstance(file, str):
        file = open(file, "rb")
    system = proto_system.MachinerySystem()
    system.ParseFromString(file.read())
    file.close()
    return system


def retrieve_gymir_result_from_file(
    file: Union[str, io.BytesIO],
) -> proto_gymir.GymirResult:
    if isinstance(file, str):
        file = open(file, "rb")
    system = proto_gymir.GymirResult()
    system.ParseFromString(file.read())
    file.close()
    return system
