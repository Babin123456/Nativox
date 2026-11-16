import os
import sys
from pathlib import Path
from typing import List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent

def get_python_executable() -> str:
    """
    Dynamically discover the best available Python interpreter across any machine / OS.
    Order of preference:
      1. LIPSYNC_PYTHON env var (if explicitly configured and exists)
      2. Local repository .venv (.venv/Scripts/python.exe on Windows, .venv/bin/python on POSIX)
      3. Active virtual environment (VIRTUAL_ENV env var)
      4. Current running Python interpreter (sys.executable)
      5. Fallback 'python' on PATH
    """
    env_py = os.getenv("LIPSYNC_PYTHON")
    if env_py and Path(env_py).exists():
        return str(Path(env_py).resolve())

    # Check local repository .venv
    venv_name = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    repo_venv = ROOT_DIR / ".venv" / venv_name
    if repo_venv.exists():
        return str(repo_venv.resolve())

    # Check active virtualenv from environment
    virtual_env = os.getenv("VIRTUAL_ENV")
    if virtual_env:
        act_py = Path(virtual_env) / venv_name
        if act_py.exists():
            return str(act_py.resolve())

    # Current running interpreter
    if sys.executable and Path(sys.executable).exists():
        return str(Path(sys.executable).resolve())

    return "python"

def resolve_model_dir(env_key: str, default_subpaths: List[str]) -> Optional[Path]:
    """
    Resolves directory paths dynamically relative to project ROOT_DIR or custom env keys.
    """
    env_val = os.getenv(env_key)
    if env_val:
        p = Path(env_val).expanduser()
        if not p.is_absolute():
            p = ROOT_DIR / p
        if p.exists():
            return p.resolve()

    for subpath in default_subpaths:
        p = (ROOT_DIR / subpath).resolve()
        if p.exists():
            return p

    return None
