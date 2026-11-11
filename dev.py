"""Atalhos de execução do projeto.

Uso:
    run dev      -> inicia o dashboard Streamlit (src/sbmm/app.py)
    run seed     -> popula o Supabase (popular_supabase.py)
    run install  -> instala as dependências do requirements.txt
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def get_python() -> str:
    venv_py = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if venv_py.exists():
        return str(venv_py)
    return sys.executable

py_bin = get_python()

COMMANDS = {
    "dev": [py_bin, "-m", "streamlit", "run", "src/sbmm/app.py"],
    "seed": [py_bin, "popular_supabase.py"],
    "install": [py_bin, "-m", "pip", "install", "-r", "requirements.txt"],
}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        print(__doc__)
        return 1

    cmd = COMMANDS[args[0]] + args[1:]
    try:
        return subprocess.call(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())

