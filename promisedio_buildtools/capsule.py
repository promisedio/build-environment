import os
import re
import hashlib
import argparse


CODE_HEADER = "// Auto-generated\n\n"


class Instruction:
    argument = False
    occurrence = None
    closing_instr = False
    opening_instr = False
    keep_content = True
    strip_whitespaces = False

    def __init__(self, start, end, arg):
        self.start = start
        self.end = end
        self.arg = arg

    def execute(self, context):
        pass


class NameInstruction(Instruction):
    name = "name"
    argument = "required"
    occurrence = [0, 1]

    def __init__(self, start, end, arg):
        if not re.match(r"[a-zA-Z_]", arg):
            raise ValueError(f"Invalid '{self.name}' argument", arg)
        super().__init__(start, end, arg)


class OutputInstruction(Instruction):
    name = "output"
    argument = "required"
    occurrence = [0, 1]

    def __init__(self, start, end, arg):
        if not re.match(r"[\w_/-]", arg):
            raise ValueError(f"Invalid '{self.name}' argument", arg)
        super().__init__(start, end, arg)


class ExportInstruction(Instruction):
    name = "export"
    occurrence = 1
    argument = "optional"
    strip_whitespaces = True

    def __init__(self, start, end, arg):
        if arg and not re.match(r"[a-zA-Z_]", arg):
            raise ValueError(f"Invalid '{self.name}' argument", arg)
        super().__init__(start, end, arg)

    def execute(self, context):
        output_variable = self.arg or f"{context.module_key}_EXPORT"
        context.out_module_source += [
            f"\n/*[capsule:__exportblock__]*/\n",
            f"#define {context.module_key} {context.api_key}\n",
            f"#define {output_variable} {{\\\n"
        ] + [
            f"  [{index}] = {func.func_name},\\\n"
            for index, func in enumerate(context.functions)
        ] + [
            "}\n",
            f"/*[capsule:__endexportblock__]*/\n\n"
        ]


class CopyInstruction(Instruction):
    name = "copy"
    closing_instr = "endcopy"
    content_start = None
    content_end = None

    def execute(self, context):
        context.out_capsule_source += [
            context.module_source[self.content_start:self.content_end].strip() + "\n\n"
        ]


class EndCopyInstruction(Instruction):
    name = "endcopy"
    opening_instr = "copy"


class ExportBlockInstruction(Instruction):
    name = "__exportblock__"
    closing_instr = "__endexportblock__"
    keep_content = False
    strip_whitespaces = True


class EndExportBlockInstruction(Instruction):
    name = "__endexportblock__"
    opening_instr = "__exportblock__"
    keep_content = False


class FunctionInstruction(Instruction):
    name = "function"

    def __init__(self, start, end, match, index):
        ret, decl = [x.strip() for x in match]
        match = re.match(r"(.*)\s*\(([\s\S]*)\)", decl)
        if not match:
            raise ValueError("Invalid declaration", decl)
        func_name, func_args = match.groups()
        self.func_name = func_name.strip()
        self.func_ret = ret
        self.func_args = [x.strip() for x in func_args.strip().split(",")]
        self.func_index = index
        super().__init__(start, end, "")

    def execute(self, context):
        func_id = self.func_name.upper() + "_ID"
        context.out_capsule_source += [
            f"#define {func_id} {self.func_index}\n"
        ]
        has_state = "_ctx_var" in self.func_args
        func_args = list(self.func_args)
        if has_state:
            func_args.remove("_ctx_var")
        has_args = bool(func_args)
        if has_state:
            func_args.insert(0, "void*")
        if has_args:
            context.out_capsule_source += [
                f"#define {self.func_name}(...) \\\n"
            ]
        else:
            context.out_capsule_source += [
                f"#define {self.func_name}() \\\n"
            ]
        func_varargs = []
        if has_state:
            func_varargs.append(f"_ctx->{context.api_key}__CTX")
        if has_args:
            func_varargs.append("__VA_ARGS__")
        func_args = ", ".join(func_args)
        func_varargs = ", ".join(func_varargs)
        context.out_capsule_source += [
            f"  (({self.func_ret} (*) ({func_args}))({context.api_key}__API[{func_id}]))( \\\n",
            f"    {func_varargs})\n\n"
        ]


INSTRUCTIONS = {
    x.name: x
    for x in [
        NameInstruction,
        OutputInstruction,
        ExportInstruction,
        CopyInstruction,
        EndCopyInstruction,
        ExportBlockInstruction,
        EndExportBlockInstruction
    ]
}


class Context:
    def __init__(self, module_name, module_source, module_key, api_key, functions):
        self.module_name = module_name
        self.module_source = module_source
        self.out_module_source = []
        self.out_capsule_source = []
        self.module_key = module_key
        self.api_key = api_key
        self.functions = functions


def main(params=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    args = parser.parse_args(params)
    for dirname, dirs, files in os.walk(args.root):
        for filename in files:
            module, ext = os.path.splitext(filename)
            if ext != ".c":
                continue
            module_path = os.path.join(dirname, filename)
            generate_capsule(module, module_path, dirname)


def generate_capsule(module, module_path, dirname):
    with open(module_path, "rt") as f:
        module_source = f.read()
    instructions, errors = parse_c_file(module_source)
    if errors:
        for msg, line, extra in errors:
            extra = f": {extra}" if extra else ""
            print(f"  Line {line}: {msg}{extra}")
        return
    if not instructions:
        return
    print(f"{module_path}:")
    name = [instr for instr in instructions if instr.name == "name"]
    if name:
        module_name = name[0].arg.upper()
    else:
        module_name = module.upper().replace(".", "_").replace("-", "_") + "_API"
    output = [instr for instr in instructions if instr.name == "output"]
    if output:
        capsule_filename = output[0].arg
        if not os.path.basename(capsule_filename):
            capsule_filename = os.path.join(capsule_filename, f"{module}.h")
        else:
            capsule_filename = capsule_filename.splitext()[0] + ".h"
    else:
        capsule_filename = f"capsule/{module}.h"
    assert len(instructions)
    functions = [
        instr for instr in instructions if isinstance(instr, FunctionInstruction)
    ]
    api_key = module_name.lower() + "_" + hashlib.md5(
        repr([(x.func_name, x.func_args) for x in functions]).encode("utf-8")
    ).hexdigest()
    context = Context(module_name, module_source, module_name, api_key, functions)
    context.out_capsule_source += [
        CODE_HEADER,
        f"#ifndef CAPSULE_{module_name}\n",
        f"#define CAPSULE_{module_name}\n\n",
        f"static int {api_key}__LOADED = 0;\n",
        f"static void *{api_key}__API[{len(functions)}];\n\n",
        f"#define {module_name} {api_key}\n\n",
    ]
    context.out_module_source.append(module_source[:instructions[0].start])
    prev_instr = None
    for instr in instructions:
        if prev_instr:
            context.out_module_source.append(module_source[prev_instr.end:instr.start])
        if instr.keep_content:
            data = module_source[instr.start:instr.end]
            if instr.strip_whitespaces:
                data = data.strip() + "\n"
            context.out_module_source.append(data)
        instr.execute(context)
        prev_instr = instr
    context.out_module_source.append(module_source[instructions[-1].end:])
    context.out_capsule_source.append("#endif\n")

    has_changes = False
    out_module_source = "".join(context.out_module_source)
    out_capsule_source = "".join(context.out_capsule_source)

    if out_module_source != module_source:
        print(f"  Rewrite {module_path}")
        with open(module_path, "wt") as f:
            f.write(out_module_source)
        has_changes = True

    capsule_source = None
    capsule_path = os.path.join(dirname, capsule_filename)
    if os.path.exists(capsule_path):
        with open(capsule_path, "rt") as f:
            capsule_source = f.read()
    if out_capsule_source != capsule_source:
        os.makedirs(os.path.dirname(capsule_path), exist_ok=True)
        print(f"  Rewrite {capsule_path}")
        with open(capsule_path, "wt") as f:
            f.write(out_capsule_source)
        has_changes = True

    if not has_changes:
        print("  No changes")


def parse_c_file(source):
    errors = []
    instructions = []

    for index, match in enumerate(re.finditer(r"CAPSULE_API\s*\((.*)\)([^{;]*)", source)):
        start, end = match.span()
        try:
            instructions.append(
                FunctionInstruction(start, end, match.groups(), index)
            )
        except ValueError as e:
            errors.append((
                e.args[0],
                len(source[:start].splitlines()) + 1,
                e.args[1]
            ))

    for match in re.finditer(r"/\*\s*\[capsule:(\w*)\s*([\w_/-]*)?\s*]\s*\*/\s*", source):
        start, end = match.span()
        kind, args = match.groups()
        if kind not in INSTRUCTIONS:
            errors.append((
                "Invalid instruction",
                len(source[:start].splitlines()) + 1,
                kind
            ))
            continue
        instr = INSTRUCTIONS[kind]
        if args and not instr.argument:
            errors.append((
                f"Unexpected '{instr.name}' argument",
                len(source[:start].splitlines()) + 1,
                args
            ))
            continue
        if not args and instr.argument == "required":
            errors.append((
                f"'{instr.name}' missing required argument",
                len(source[:start].splitlines()) + 1,
                args
            ))
            continue
        try:
            instructions.append(instr(start, end, args))
        except ValueError as e:
            errors.append((
                e.args[0],
                len(source[:start].splitlines()) + 1,
                e.args[1]
            ))
            continue

    if not instructions or errors:
        return None, errors

    instructions.sort(key=lambda x: x.start)
    for index, instr in enumerate(instructions):
        if instr.opening_instr:
            try:
                if instructions[index - 1].name != instr.opening_instr:
                    raise IndexError()
            except IndexError:
                errors.append((
                    f"Missing opening '{instr.opening_instr}' instruction",
                    len(source[:instr.start].splitlines()) + 1,
                    None
                ))
        if instr.closing_instr:
            try:
                if instructions[index + 1].name != instr.closing_instr:
                    raise IndexError()
            except IndexError:
                errors.append((
                    f"Missing closing '{instr.closing_instr}' instruction",
                    len(source[:instr.start].splitlines()) + 1,
                    None
                ))

    for instr_class in INSTRUCTIONS.values():
        if instr_class.occurrence:
            items = [instr for instr in instructions if type(instr) is instr_class]
            if isinstance(instr_class.occurrence, int):
                min_occurrence = max_occurrence = instr_class.occurrence
            else:
                min_occurrence, max_occurrence = instr_class.occurrence
            if len(items) < min_occurrence:
                errors.append((
                    f"Missing required '{instr_class.name}' instruction",
                    1,
                    None
                ))
            if len(items) > max_occurrence:
                if max_occurrence == 1:
                    for item in items[max_occurrence:]:
                        errors.append((
                            f"Only one '{instr_class.name}' instruction is allowed",
                            len(source[:item.start].splitlines()) + 1,
                            None
                        ))
                else:
                    for item in items[max_occurrence:]:
                        errors.append((
                            f"Too much '{instr_class.name}' instructions",
                            len(source[:item.start].splitlines()) + 1,
                            None
                        ))

    if errors:
        return None, errors

    final_instructions = []
    for index, instr in enumerate(instructions):
        if instr.closing_instr:
            instr.content_start = instr.end
            instr.content_end = instructions[index + 1].start
            instr.end = instructions[index + 1].end
        elif instr.opening_instr:
            continue
        final_instructions.append(instr)

    return final_instructions, None


if __name__ == "__main__":
    main()
