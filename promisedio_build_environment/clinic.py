import sys
from . myclinic import main as clinic_main
from . capsule import main as capsule_main


def run():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: clinic PATH\n")
        sys.exit(-1)
    capsule_main([sys.argv[1]])
    clinic_main(["--make", "--srcdir"] + sys.argv[1:])


if __name__ == "__main__":
    run()

