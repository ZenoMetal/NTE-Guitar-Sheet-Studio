# Contributing

Bug reports and focused improvements are welcome. Please describe your operating
system, Python version, NTE launcher (Steam or standalone), and the exact steps
needed to reproduce an issue. Do not post credentials, personal save data, or
copyrighted song arrangements you do not have permission to share.

For text parsing problems, include a small notation sample, the selected key
layout and timing settings. For MIDI issues, a minimal original test file is
preferable to a complete song.

Before submitting a change, run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q main.py nte_studio
QT_QPA_PLATFORM=offscreen python main.py --self-test
```

The `QT_QPA_PLATFORM` prefix shown above is for POSIX shells. On Windows, set
the environment variable separately before running `python main.py --self-test`.

Keep all application text and documentation in English. Preserve the
no-overwrite installation behavior and do not label locally generated IDs as
online share codes. Never use the real game cache for automated tests.
