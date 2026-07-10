# ---------------------------------------------------------------------------
# Stage 1: build PyMFEM (slow ~20 min, but cached — only rebuilds if this
# stage itself changes, never when api/requirements.txt changes)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS mfem-builder

RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    libopenmpi-dev \
    openmpi-bin \
    swig \
    git

# Build-time Python deps for PyMFEM's parallel build.
# Pins kept in sync with api/requirements.txt (mpi4py, swig).
RUN pip install --no-cache-dir setuptools numpy mpi4py==4.1.1 swig==4.4.0

# Build MFEM + PyMFEM with parallel and GSLIB support into a wheel
RUN git clone https://github.com/mfem/PyMFEM.git /pymfem_installation && \
    cd /pymfem_installation && \
    pip wheel ./ --no-deps -w /wheels -C"with-parallel=Yes" -C"with-gslib=Yes"

# ---------------------------------------------------------------------------
# Stage 2: dev image
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# Build tools and MPI (kept in the dev image for development use)
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    libopenmpi-dev \
    openmpi-bin \
    swig \
    git

# X11 display for matplotlib (x11-apps is development/testing only)
RUN apt-get install -y \
    python3-tk \
    tk-dev \
    x11-apps

# OpenGL and X11 libraries for gmsh
RUN apt-get install -y \
    libgl1 \
    libglu1-mesa \
    libxrender1 \
    libxcursor1 \
    libxft2 \
    libxinerama1

RUN pip install setuptools

# Install the PyMFEM wheel prebuilt in stage 1
COPY --from=mfem-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl

# App requirements last: editing api/requirements.txt only rebuilds from here,
# not the MFEM build above
COPY ./api/requirements.txt /temp/api/requirements.txt
RUN pip install --no-cache-dir -r /temp/api/requirements.txt

CMD ["sleep", "infinity"]
