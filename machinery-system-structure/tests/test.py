import os

from MachSysS.utility import retrieve_machinery_system_from_file
from MachSysS.convert_to_feems import convert_proto_propulsion_system_to_feems

if __name__ == "__main__":
    path = os.path.join("electric_propulsion_system.mss")
    system_proto = retrieve_machinery_system_from_file(path)
    system_feems = convert_proto_propulsion_system_to_feems(system_proto)
    print(system_feems.switchboards)
