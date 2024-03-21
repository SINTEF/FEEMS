ECHO Building library from the jupyter notebook
nbdev_export
nbdev_test
nbdev_clean
ECHO Build a wheel
python setup.py sdist bdist_wheel
