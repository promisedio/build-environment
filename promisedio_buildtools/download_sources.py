import os
import sysconfig
import requests
import tempfile
import subprocess
import hashlib
import json


def get_content(ver, path):
    print(f"Download {ver}: {path}")
    url = f"https://raw.githubusercontent.com/python/cpython/{ver}/{path}"
    return requests.get(url).content


def remove_comments(code):
    new_code = []
    comment_block = False
    empty_line = False
    for line in code.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith(b"//"):
            continue
        if stripped_line.startswith(b"/*"):
            comment_block = True
        if comment_block:
            if stripped_line.endswith(b"*/"):
                comment_block = False
            continue
        if empty_line and not stripped_line:
            continue
        empty_line = not stripped_line
        new_code.append(line)
    return b"\n".join(new_code)


def ensure_dict(d):
    if not isinstance(d, dict):
        return {}
    return d


def get_source_code(version, path, target, c_names=None, exclude_c_names=None,
                    wrap_guards=None, stub_template=None):
    if wrap_guards is None:
        wrap_guards = path.endswith(".h") or path.endswith(".c")
    path = path.format(version=version)
    target = target.format(version=version)
    code = get_content("v" + version, path)
    if c_names or exclude_c_names:
        with tempfile.NamedTemporaryFile(suffix=".c") as f:
            f.write(code)
            options = [
                f"-I{sysconfig.get_config_var('INCLUDEDIR')}",
                f"-I{sysconfig.get_config_var('INCLUDEPY')}"
            ]
            if c_names:
                options += [f"-D{d['ifdef']}=1" for d in c_names.values() if ensure_dict(d).get("ifdef")]
            ret = subprocess.run(
                ["clang", "-Xclang", "-ast-dump=json", *options, f.name],
                capture_output=True
            )
            dat = json.loads(ret.stdout)
        if c_names:
            code_pieces = []
            for node in dat["inner"]:
                if node["kind"].endswith("Decl") and node.get("name") in c_names:
                    ifdef = ensure_dict(c_names[node["name"]]).get("ifdef")
                    only_source_hash = ensure_dict(c_names[node["name"]]).get("only_source_hash")
                    start = node["range"]["begin"]["offset"]
                    end = node["range"]["end"]["offset"]
                    if node["kind"] != "TypedefDecl":
                        end += 1
                    piece = code[start: end]
                    if node["kind"] == "TypedefDecl":
                        piece += node["name"].encode("utf-8")
                    if node["kind"] != "FunctionDecl":
                        piece += b";"
                    if ifdef:
                        piece = b"#ifdef " + ifdef.encode("utf-8") + b"\n" + piece + b"\n#endif"
                    if only_source_hash:
                        piece_hash = hashlib.md5(piece).hexdigest()[:8].encode("utf-8")
                        piece = b"\n".join(b"// %s" % line for line in piece.splitlines())
                        piece = b"#define %s_hash 0x%s\n%s" % (node["name"].encode("utf-8"), piece_hash, piece)
                    code_pieces.append(piece)
            code = b"\n\n".join(code_pieces)
        else:
            code = bytearray(code)
            blocks = []
            for node in dat["inner"]:
                if node["kind"].endswith("Decl") and node.get("name") in exclude_c_names:
                    start = node["range"]["begin"]["offset"]
                    end = node["range"]["end"]["offset"]
                    if node["kind"] == "FunctionDecl":
                        end += 1
                    blocks.append((start, end))
            blocks.reverse()
            for start, end in blocks:
                code[start: end] = b"//"

    code = remove_comments(code)
    dirname = os.path.dirname(target)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    if wrap_guards:
        filename = os.path.split(target)[1]
        guard = ("HEADER_" + filename.replace(".", "_").upper()).encode("utf-8")
        code = b"#ifndef %s\n#define %s\n\n%s\n\n#endif" % (guard, guard, code)
    with open(target, "wt") as f:
        f.write(code.decode("utf-8"))


def main():
    items = json.loads(open("sources.json", "rt").read())
    for item in items:
        for version in sorted(item.pop("version")):
            get_source_code(version, **item)


if __name__ == "__main__":
    main()
