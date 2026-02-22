import os
from random import random

from MachSysS.convert_gymir_result_to_proto import GymirResultConverter


def test_convert_gymir_result_to_proto():
    gymir_result_converter = GymirResultConverter()
    package_dir = os.path.dirname(os.path.abspath(__file__))
    path_to_csv_file = os.path.join(package_dir, "Timeseries1648799237.csv")
    
    gymir_result_converter.read_csv(path_to_csv_file, auxiliary_load_kw=100, name="test")
    assert len(gymir_result_converter.gymir_result.result) == 26
    
    # Check modification
    for each_instance in gymir_result_converter.gymir_result.result:
        each_instance.power_kw = random() * 1000
    
    # Check writing (to a temporary file)
    output_file = os.path.join(package_dir, "timeseries_test_out.csv")
    gymir_result_converter.to_csv(output_file)
    
    assert os.path.exists(output_file)
    os.remove(output_file)
