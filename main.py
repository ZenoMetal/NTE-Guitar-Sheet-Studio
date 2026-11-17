"""Start the desktop application. See README.md for Windows/Linux launchers."""
import sys

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        from nte_studio.self_test import run
        raise SystemExit(run())
    from nte_studio.ui import main
    raise SystemExit(main())
