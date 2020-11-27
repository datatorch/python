import os

CONDA_EXE = "CONDA_EXE"


def get_conda_executable(default_exec: str = "conda"):
    if "CONDA_EXE" in os.environ:
        conda_bin_dir = os.path.dirname(os.getenv(CONDA_EXE))
