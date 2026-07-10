# syntax=docker/dockerfile:1
#
# Production image for the JSTC backend. Build from the repo root:
#     docker build -f api/Dockerfile -t jstc-api .
#
# Two stages: the slow PyMFEM compile is isolated (and layer-cached) in
# stage 1, so editing app code or requirements never re-triggers it.

# ---------------------------------------------------------------------------
# Stage 1: build the PyMFEM wheel (~20 min; cached unless this stage changes)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS mfem-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ libopenmpi-dev openmpi-bin swig git \
    && rm -rf /var/lib/apt/lists/*

# Build-time deps for PyMFEM's parallel build (pins mirror requirements.txt).
RUN pip install --no-cache-dir setuptools numpy mpi4py==4.1.1 swig==4.4.0

# Build MFEM + PyMFEM (parallel + GSLIB) into a wheel.
RUN git clone https://github.com/mfem/PyMFEM.git /pymfem \
    && cd /pymfem \
    && pip wheel ./ --no-deps -w /wheels -C"with-parallel=Yes" -C"with-gslib=Yes"

# ---------------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Runtime libraries: MPI (MFEM/mpi4py), OpenGL/X11 (gmsh), OpenMP (MKL/numba).
# build-essential + libopenmpi-dev are needed because mpi4py compiles against
# MPI during pip install; kept minimal, no dev/X11-apps tooling.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ libopenmpi-dev openmpi-bin swig \
    libgl1 libglu1-mesa libxrender1 libxcursor1 libxft2 libxinerama1 \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Prebuilt MFEM wheel first, then the app requirements (better layer caching).
COPY --from=mfem-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY api/ ./

# Run as a non-root user.
RUN useradd -m -u 1001 appuser && chown -R appuser /app
USER appuser

# Production defaults - all overridable at deploy time. The thread counts and
# worker count are the tuning dials for your instance size (see comments):
#   WEB_CONCURRENCY = gunicorn workers (processes)  -> concurrent FEM solves
#   *_NUM_THREADS   = threads per solve (MKL/gmsh)  -> speed of each solve
# Keep workers x threads <= vCPUs. Default targets a ~2 vCPU / 2 GB box:
# 2 workers (crash isolation + 2 concurrent solves), 1 thread each.
ENV JSTC_WARMUP=1 \
    WEB_CONCURRENCY=2 \
    JSTC_MESH_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/health" || exit 1

# Gunicorn manages Uvicorn workers. Binds $PORT (Cloud Run/Fly inject it).
# Long timeout for the occasional heavy FEM solve; max-requests recycles
# workers to shrug off any native memory growth.
CMD exec gunicorn main:app \
    -k uvicorn.workers.UvicornWorker \
    -w "${WEB_CONCURRENCY}" \
    -b "0.0.0.0:${PORT}" \
    --timeout 120 --graceful-timeout 30 \
    --max-requests 300 --max-requests-jitter 60 \
    --access-logfile - --error-logfile -
