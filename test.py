import sys
import os

# 1. Get the full path to the current Python executable
print(f"Executable: {sys.executable}")

# 2. Check if you are in a virtual environment (venv)
# If prefix != base_prefix, you are in a venv.
print(f"Is Virtual Env: {sys.prefix != sys.base_prefix}")
print(f"Env Path: {sys.prefix}")

# 3. Check for Conda specifically
conda_env = os.environ.get('CONDA_DEFAULT_ENV')
if conda_env:
    print(f"Conda Env Name: {conda_env}")
