import sys

from miaguard.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["masked-mia", *sys.argv[1:]]))

