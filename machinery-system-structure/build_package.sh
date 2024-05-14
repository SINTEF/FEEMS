set -e
bash ./compile_proto.sh
echo "Exporting notebooks"
nbdev_export
echo "Running tests"
nbdev_test
echo "Formatting code"
black .
echo "Building package"
python -m build