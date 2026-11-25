"""Foundation command line entry point."""
import argparse
from . import __version__

def main():
    parser = argparse.ArgumentParser(description="Human3D 2.0")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()

if __name__ == "__main__":
    main()
