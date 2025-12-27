#! /bin/bash

# Install API Python Dependencies
pip install --no-cache-dir -r /JSTC/api/requirements.txt

# Build pymfem from source and install with parallel and gslib
apt-get update && apt-get install -y build-essential g++ libopenmpi-dev openmpi-bin swig
git clone https://github.com/mfem/PyMFEM.git /pymfem_installation
cd /pymfem_installation 
pip install ./ -C"with-parallel=Yes" -C"with-gslib=Yes" --verbose
python setup.py clean --all
