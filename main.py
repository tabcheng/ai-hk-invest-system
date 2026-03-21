"""Backward-compatible runner wrapper.

Preferred scheduled entrypoint is now `python -m src.daily_runner`.
This file remains to avoid breaking existing invocations that still call
`python main.py`.
"""

from src.daily_runner import main


if __name__ == "__main__":
    main()
