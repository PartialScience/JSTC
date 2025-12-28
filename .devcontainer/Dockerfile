FROM python:3.12-slim

COPY ./api/requirements.txt /temp/api/requirements.txt

# Install needed Python packages
RUN pip install setuptools
RUN pip install --no-cache-dir -r /temp/api/requirements.txt

# Install MFEM and PyMFEM dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    libopenmpi-dev \
    openmpi-bin \
    swig \
    git 
# Install dependencies for X11 display with matplotlib (this is not needed in the final build since x11-apps is only for development/testing)
RUN apt-get install -y \
    python3-tk \
    tk-dev \
    x11-apps
# Build and install MFEM with parallel and GSLIB support
RUN \
    git clone https://github.com/mfem/PyMFEM.git /pymfem_installation &&\
    cd /pymfem_installation &&\
    pip install ./ -C"with-parallel=Yes" -C"with-gslib=Yes"

CMD ["sleep", "infinity"]