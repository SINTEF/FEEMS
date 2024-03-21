protoc -I=proto --proto_path=proto --python_out=MachSysS proto/system_structure.proto proto/gymir_result.proto proto/feems_result.proto
sed -e 's/import system_structure_pb2/from . import system_structure_pb2/' MachSysS/feems_result_pb2.py > MachSysS/feems_result_pb2_1.py
mv MachSysS/feems_result_pb2_1.py MachSysS/feems_result_pb2.py
nbdev_export
nbdev_test
black .
python setup.py sdist bdist_wheel