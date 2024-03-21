# RunFeemsSim Package

> The RunFeemsSim package is a Python package for running FEEMS simulations. It provides a simple 
> interface for running FEEMS simulations and for visualizing the results. It also provides a basic 
> pms model to apply for an electric power system that has a functionality of load dependent 
> start-stop of gensets.

## Installation of the package
The package is distributed by the Azure Artifacts package manager. To install the package, 
you need to install artifacts-keyring package and should have a valid Azure DevOps account. 
```sh
pip install artifacts-keyring
```
Then, you need to add the package source to your pip configuration. You can do this by copying 
the pip configuration file (pip.conf for macOS and Linux or pip.ini for Windows) to your 
virtual environment directory or base python directory. The file should contain the following lines:
```sh
[global]
extra-index-url=https://pkgs.dev.azure.com/SintefOceanEnergySystem/_packaging/SintefOceanEnergySystem/pypi/simple/
```
If you already have a pip configuration file, you can add the above lines to the file. Finally, 
you can install the package by running the following command:
```sh
pip install RunFeemsSim
```
 
## Installation of the development environment
For the development, one should create a virtual environment and install the package using the 
requirements.txt file. First, create a virtual environment and activate it. 
```sh 
python -m venv venv
source venv/bin/activate
```
Then, you need to add the package source to your pip configuration. You can do this by copying 
the pip configuration file (pip.conf for macOS and Linux or pip.ini for Windows) to your venv 
directory or base python directory. The file should contain the following lines:
```sh
[global]
extra-index-url=https://pkgs.dev.azure.com/SintefOceanEnergySystem/_packaging/SintefOceanEnergySystem/pypi/simple/
```

Then, install the package using the requirements.txt file.
```sh
pip install -r requirements.txt
```

## Usage


