import sys

from miaguard.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["direct-rag-mia", *sys.argv[1:]]))
