"""Atalhos de execução do projeto.

Uso:
    run dev      -> inicia o dashboard Streamlit (app_demo.py)
    run seed     -> popula o Supabase (popular_supabase.py)
    run install  -> instala as dependências do requirements.txt
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

COMMANDS = {
    "dev": [sys.executable, "-m", "streamlit", "run", "app_demo.py"],
    "seed": [sys.executable, "popular_supabase.py"],
    "install": [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
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

