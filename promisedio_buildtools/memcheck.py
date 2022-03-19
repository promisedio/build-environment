import re
import sys


class Ref:
    def __init__(self, type):
        self.type = type
        self.refcnt = 1

    def __str__(self):
        return f"{self.type}({self.refcnt})"


def main():
    mallocs = []
    objects = {}
    types = {}

    def print_objects():
        for addr, ref in objects.items():
            print(f"{addr}\t{ref}")

    def print_mallocs():
        for addr in mallocs:
            if addr in objects:
                print(f"{addr}\t{objects[addr]}")
            else:
                print(f"{addr}\tRAW")

    def print_types():
        for tp in types:
            print(f"{tp} new:{types[tp]['new']} del:{types[tp]['del']}")

    def print_header(title):
        length = 40
        if not title:
            print("=" * length)
            return
        rest = length - len(title) - 2
        left_pad = rest // 2
        right_pad = rest - left_pad
        print("=" * left_pad, title, "=" * right_pad)

    def print_stats():
        print_header("Mallocs")
        print_mallocs()
        print_header("Objects")
        print_objects()
        print_header("Types")
        print_types()

    def print_leaks():
        if objects:
            print_header("Leaks report (Objects)")
            print_objects()
        if mallocs:
            print_header("Leaks report (Mallocs)")
            print_mallocs()
        if not (objects and mallocs):
            print_header("Great! No leaks")
        if types:
            print_types()

    for line in sys.stdin:
        line = line.strip()
        print(line)
        if not line:
            continue
        if line == "#ALLOCSTAT":
            print_stats()
            continue
        if not line.startswith("#"):
            continue
        match = re.match(r"#(\w+)\s*\((.*)\)", line.split("--", 1)[0].strip())
        if not match:
            continue
        action, args = match.groups()
        args = [x.strip() for x in args.split(",")]
        if action == "Malloc":
            mallocs.append(args[0])
        elif action == "Free":
            if args[0] not in mallocs:
                print_header("Missing memory")
                print(action)
                print(args)
                print(mallocs)
                print_header("")
            else:
                mallocs.remove(args[0])
        elif action == "New":
            if args[0] in objects:
                print_header("Already allocated")
                print(action)
                print(args)
                print(objects)
                print_header("")
            else:
                objects[args[0]] = Ref(args[1])
            types.setdefault(args[1], {"new": 0, "del": 0})["new"] += 1
        elif action == "Delete":
            if args[0] not in objects:
                print_header("Missing object")
                print(action)
                print(args)
                print(objects)
                print_header("")
            else:
                del objects[args[0]]
            types.setdefault(args[1], {"new": 0, "del": 0})["del"] += 1
        elif action in ("Incref", "Enter", "Resized"):
            if args[0] in objects:
                objects[args[0]].refcnt += 1
            else:
                objects[args[0]] = Ref(args[1])
        elif action in ("Decref", "Resize"):
            if args[0] in objects:
                objects[args[0]].refcnt -= 1
                if objects[args[0]].refcnt == 0:
                    del objects[args[0]]
            else:
                print_header("Missing object")
                print(action)
                print(args)
                print(objects)
                print_header("")

    print_leaks()


if __name__ == "__main__":
    main()
