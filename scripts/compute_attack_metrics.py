import sys

from miaguard.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["metrics", *sys.argv[1:]]))

