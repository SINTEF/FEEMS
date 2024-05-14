set -e
echo "Building protobuf files"
protoc -I=proto --proto_path=proto --pyi_out=MachSysS --python_out=MachSysS proto/system_structure.proto proto/gymir_result.proto proto/feems_result.proto
echo "Fixing imports in protobuf files"

# loop over files and replace import system_structure_pb2
# Determine OS platform
OS="$(uname -s)"
case "$OS" in
  Linux*)     machine=Linux;;
  Darwin*)    machine=Mac;;
  *)          machine="UNKNOWN:${OS}"
esac
echo "Detected OS: $machine"

# Run commands based on the detected OS
case "$machine" in
  Linux)   echo "Running Linux-specific commands"
           # Linux specific commands here
           for file in MachSysS/*_pb2.py MachSysS/*_pb2.pyi; do
               sed -i 's/import system_structure_pb2/from . import system_structure_pb2/' $file
           done
           ;;
  Mac)     echo "Running macOS-specific commands"
           for file in MachSysS/*_pb2.py MachSysS/*_pb2.pyi; do
               sed -i '' 's/import system_structure_pb2/from . import system_structure_pb2/' $file
           done
           ;;
  *)       echo "Unsupported OS. Exiting script."
           exit 1
           ;;
esac