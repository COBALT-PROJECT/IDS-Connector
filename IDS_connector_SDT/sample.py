#!/usr/bin/env python3
"""sample.py — a tiny, well-structured Python script.

Usage:
  python sample.py --name Allen --repeat 3
"""

from __future__ import annotations
import argparse
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class Greeter:
    name: str
    repeat: int = 1

    def greet(self) -> str:
        """Return a greeting string repeated `repeat` times."""
        message = f"Hello, {self.name}!"
        return "\n".join([message] * max(1, self.repeat))

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Say hello a few times.")
    parser.add_argument("--name", default="World", help="Name to greet.")
    parser.add_argument("--repeat", type=int, default=1, help="How many times to repeat.")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    greeter = Greeter(name=args.name, repeat=args.repeat)
    logging.info("Preparing greeting...")
    print(greeter.greet())

if __name__ == "__main__":
    main()
