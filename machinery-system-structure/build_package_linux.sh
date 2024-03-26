set -e
echo "Building protobuf files"
protoc -I=proto --proto_path=proto --python_out=MachSysS proto/system_structure.proto proto/gymir_result.proto proto/feems_result.proto
echo "Fixing imports in protobuf files"
sed -i 's/import system_structure_pb2/from . import system_structure_pb2/' MachSysS/feems_result_pb2.py
echo "Exporting notebooks"
nbdev_export
echo "Running tests"
nbdev_test
echo "Formatting code"
black .
echo "Building package"
python -m build
