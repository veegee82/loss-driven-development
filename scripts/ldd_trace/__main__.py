"""Allow `python -m ldd_trace ...`"""
from ldd_trace.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
