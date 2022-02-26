import os
import re
import json
import hashlib


code_header = "// Auto-generated\n\n"


def main():
    capsules = json.loads(open("capsules.json", "rt").read())
    include = format_list(capsules.get("include"))
    for path, params in capsules["modules"].items():
        module_include = include + format_list(params.pop("include", None))
        generate_capsule(path, include=module_include, **params)


def format_list(value, mapping=None):
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]
    return [str(x).format_map(mapping or {}) for x in value]


def generate_capsule(
        path,
        include=None,
        output="capsule/{module}.h",
        export="{module}_export.h",
        sources="{module}.c",
        extend=None
):
    print(path)
    module = os.path.split(path)[1]
    if not os.path.exists(path) or not os.path.isdir(path):
        raise FileNotFoundError(path)
    mapping = {
        "module": module,
        "path": path
    }
    output = format_list(output, mapping)
    if not output:
        raise ValueError("`output` must be specified")
    output = os.path.join(path, output[0])

    export = format_list(export, mapping)
    if not export:
        raise ValueError("`export` must be specified")
    export = os.path.join(path, export[0])

    sources = format_list(sources, mapping)
    if not sources:
        raise ValueError("`sources` must be specified")

    extend = format_list(extend, mapping)

    functions = {}
    for source in sources:
        with open(os.path.join(path, source), "rt") as f:
            data = f.read()
        result = parse_c_file(data)
        if result:
            for key, value in result.items():
                functions.setdefault(key, []).extend(value)

    if not functions:
        return

    hash_keys = {}
    for api_key, funcs in functions.items():
        hash_keys[api_key] = hashlib.md5(repr(funcs).encode("utf-8")).hexdigest()

    if os.path.dirname(output):
        os.makedirs(os.path.dirname(output), exist_ok=True)
    if os.path.dirname(export):
        os.makedirs(os.path.dirname(export), exist_ok=True)

    with open(output, "wt") as f1:
        with open(export, "wt") as f2:
            f1.write(code_header)
            f1.write(f"#ifndef CAPSULE_{module.upper()}_API\n")
            f1.write(f"#define CAPSULE_{module.upper()}_API\n\n")
            if include:
                for item in include:
                    f1.write(f'#include "{item}"\n')
                f1.write("\n")
            f2.write(code_header)
            for api_key, funcs in functions.items():
                hash_key = api_key + "_" + hash_keys[api_key]
                f1.write(f"static int {hash_key}__api_loaded = 0;\n")
                f1.write(f"static void *{hash_key}__api[{len(funcs)}];\n\n")
                f1.write(f"#define {api_key.upper()} {hash_key}\n\n")
                f2.write(f"#define {api_key.upper()} {hash_key}\n\n")
                f2.write(f"#define {api_key.upper()}_CAPSULE {{\\\n")
                for index, func in enumerate(funcs):
                    ret = func["ret"]
                    name = func["name"]
                    args = list(func["args"])
                    func_id = name.upper() + "_ID"
                    f1.write(f"#define {func_id} {index}\n")
                    f2.write(f"  [{index}] = {name},\\\n")
                    has_state = "_ctx_var" in args
                    if has_state:
                        args.remove("_ctx_var")
                    has_args = bool(args)
                    if has_state:
                        args.insert(0, "void*")
                    if has_args:
                        f1.write(f"#define {name}(...) \\\n")
                    else:
                        f1.write(f"#define {name}() \\\n")
                    varargs = []
                    if has_state:
                        varargs.append(f"_ctx->{hash_key}__ctx")
                    if has_args:
                        varargs.append("__VA_ARGS__")
                    args = ", ".join(args)
                    varargs = ", ".join(varargs)
                    # f1.write(f"  (*({ret} (*) ({args}))(_ctx->{hash_key}__api[{func_id}]))( \\\n")
                    f1.write(f"  (({ret} (*) ({args}))({hash_key}__api[{func_id}]))( \\\n")
                    f1.write(f"    {varargs})\n\n")
                f2.write("}\n\n")

            if extend:
                for item in extend:
                    f1.write(open(os.path.join(path, item), "rt").read() + "\n")

            f1.write("#endif\n")


def parse_c_file(data):
    result = {}
    functions = re.findall(r"CAPSULE_API\((.*),\s*(.*)\)([^{;]*)", data)
    for key, ret, decl in functions:
        key = key.strip()
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]+$", key):
            raise ValueError("Invalid key", key, decl)
        ret = ret.strip()
        decl = decl.strip()
        match = re.match(r"(.*)\(([\s\S]*)\)", decl)
        if not match:
            raise ValueError("Invalid declaration", key, decl)
        func_name, func_args = match.groups()
        func_name = func_name.strip()
        func_args = [x.strip() for x in func_args.strip().split(",")]
        result.setdefault(key.lower(), []).append({
            "name": func_name,
            "ret": ret,
            "args": func_args
        })
    return result


if __name__ == "__main__":
    main()
