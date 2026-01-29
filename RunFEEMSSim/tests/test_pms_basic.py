import os
import numpy as np
from MachSysS.utility import retrieve_machinery_system_from_file
from RunFeemsSim.pms_basic import get_min_load_table_dict_from_proto_system

def test_get_min_load_table_dict_from_proto_system():
    # Construct absolute path to the data file in the same directory as this test file
    package_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(package_dir, "system_proto.mss")
    
    system_proto = retrieve_machinery_system_from_file(path)
    load_table_dict = get_min_load_table_dict_from_proto_system(system_proto)
    
    np.testing.assert_equal(len(load_table_dict), 14)
    # Optional: Verify content if needed, but the notebook just printed it
    # print(load_table_dict)
