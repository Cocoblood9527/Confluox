from __future__ import annotations

import signal
import time


_RUNNING = True


def _handle_signal(signum, frame) -> None:
    del signum, frame
    global _RUNNING
    _RUNNING = False


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    while _RUNNING:
        time.sleep(0.5)


if __name__ == "__main__":
    main()
