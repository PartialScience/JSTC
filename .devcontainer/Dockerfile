FROM python:3.12-slim

COPY ./api/requirements.txt /temp/api/requirements.txt

RUN pip install setuptools
RUN pip install --no-cache-dir -r /temp/api/requirements.txt

# Build pymfem from source and install with parallel and gslib
RUN apt-get update && apt-get install -y build-essential g++ libopenmpi-dev openmpi-bin swig git
RUN \
    git clone https://github.com/mfem/PyMFEM.git /pymfem_installation &&\
    cd /pymfem_installation &&\
    pip install ./ -C"with-parallel=Yes" -C"with-gslib=Yes"

CMD ["sleep", "infinity"]