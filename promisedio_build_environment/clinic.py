import re
import sys
from . import cpp

sys.modules["cpp"] = sys.modules["promisedio_build_environment.cpp"]

from . pyclinic import *
from . pyclinic import main as clinic_main


readme_contents = {}

format_to_signature = {
    "s": "str",                                 # [const char *]
    "s*": "Union[str, bytes, bytearray]",       # [Py_buffer]
    "s#": "Union[str, bytes]",                  # [const char *, Py_ssize_t]
    "z": "Optional[str]",                       # [const char *]
    "z*": "Optional[Union[str, bytes, bytearray]]", # [Py_buffer]
    "z#": "Optional[Union[str, bytes]]",        # [const char *, Py_ssize_t]
    "y": "bytes",                               # [const char *]
    "y*": "Union[bytes, bytearray]",            # [Py_buffer]
    "y#": "bytes",                              # [const char *, Py_ssize_t]
    "S": "bytes",                               # [PyBytesObject *]
    "Y": "bytearray",                           # [PyByteArrayObject *]
    "u": "str",                                 # [const Py_UNICODE *]
    "u#": "str",                                # [const Py_UNICODE *, Py_ssize_t]
    "Z": "Optional[str]",                       # [const Py_UNICODE *]
    "Z#": "Optional[str]",                      # [const Py_UNICODE *, Py_ssize_t]
    "U": "str",                                 # [PyObject *]
    "w*": "bytearray",                          # [Py_buffer]
    "es": "str",                                # [const char *encoding, char **buffer]
    "et": "Union[str, bytes, bytearray]",       # [const char *encoding, char **buffer]
    "es#": "str",                               # [const char *encoding, char **buffer, Py_ssize_t *buffer_length]
    "et#": "Union[str, bytes, bytearray]",      # [const char *encoding, char **buffer, Py_ssize_t *buffer_length]
    "b": "int",                                 # [unsigned char]
    "B": "int",                                 # [unsigned char]
    "h": "int",                                 # [short int]
    "H": "int",                                 # [unsigned short int]
    "i": "int",                                 # [int]
    "I": "int",                                 # [unsigned int]
    "l": "int",                                 # [long int]
    "k": "int",                                 # [unsigned long]
    "L": "int",                                 # [long long]
    "K": "int",                                 # [unsigned long long]
    "n": "int",                                 # [Py_ssize_t]
    "c": "Union[bytes, bytearray]",             # [char]
    "C": "str",                                 # [int]
    "f": "float",                               # [float]
    "d": "float",                               # [double]
    "D": "complex",                             # [Py_complex]
    "O": "object",
    "O!": "object",
    "O&": "object",
    "p": "bool",                                # [bool predicate]
}


def get_parameter_annotation(param):
    arg = param.name
    arg_type = getattr(param.converter, "typed", None)
    if not arg_type and param.converter.format_unit in format_to_signature:
        arg_type = format_to_signature[param.converter.format_unit]
    if not arg_type:
        arg_type = "Any"
    arg += ": " + arg_type
    if param.default is not unspecified:
        arg += " = " + repr(param.default)
    return arg


def get_return_annotation(func):
    converter = func.return_converter
    annotation = getattr(converter, "typed", None)
    return annotation or "Any"


docstring_for_c_string = CLanguage.docstring_for_c_string


def docstring_for_c_string_from_readme(self, f):
    result = docstring_for_c_string(self, f)
    module = readme_contents.setdefault(f.module.name, {"classes": {}, "functions": {}})
    if f.cls:
        module["classes"].setdefault(f.cls.name, {})[f.name] = f
    else:
        module["functions"][f.name] = f
    return result


CLanguage.docstring_for_c_string = docstring_for_c_string_from_readme


def generate_readme():
    output = []

    def replacer(m):
        name = m.group(1)
        if name in functions or name in classes:
            return f"[{name}](#{name.lower()})"
        return f"`{name}`"

    def generate_function(name, f):
        args = [get_parameter_annotation(p) for p in list(f.parameters.values())[1:]]
        returns = get_return_annotation(f)
        output.append(f"#### {name}")
        # output.append(f"##### Signature")
        output.append("```python")
        output.append(f"{name}({', '.join(args)}) -> {returns}")
        output.append("```")
        _, doc = f.docstring.split("--", 1)
        doc = doc.strip()
        doc = re.sub(r"`([^`]*)`", replacer, doc)
        # output.append(f"##### Description")
        output.append(doc)
        output.append("")

    for module in sorted(readme_contents):
        classes = readme_contents[module]["classes"]
        functions = readme_contents[module]["functions"]
        output.append(f"# {module} module")
        for function in sorted(functions):
            generate_function(function, functions[function])
        for cls in sorted(classes):
            output.append(f"### {cls}")
            functions = classes[cls]
            for function in sorted(functions):
                generate_function(f"{cls}.{function}", functions[function])
        output.append("")

        template = open("README.md").read()
        pattern = rf"<!---\s*template:\[{module}\]\s*-->[\s\S]*<!---\s*end:\[{module}\]\s*-->"

        def repl(m):
            return (
                f"<!--- template:[{module}] -->\n" +
                "\n".join(output) +
                f"\n<!--- end:[{module}] -->"
            )

        doc = re.sub(pattern, repl, template, 1)
        if doc != template:
            open("README.md", "wt").write(doc)


def rebuild_func(fn, consts):
    code = type(fn.__code__)(fn.__code__.co_argcount,
                             fn.__code__.co_posonlyargcount,
                             fn.__code__.co_kwonlyargcount,
                             fn.__code__.co_nlocals,
                             fn.__code__.co_stacksize,
                             fn.__code__.co_flags,
                             fn.__code__.co_code,
                             consts,
                             fn.__code__.co_names,
                             fn.__code__.co_varnames,
                             fn.__code__.co_filename,
                             fn.__code__.co_name,
                             fn.__code__.co_firstlineno,
                             fn.__code__.co_lnotab,
                             fn.__code__.co_freevars,
                             fn.__code__.co_cellvars
                             )
    new_fn = type(fn)(code, fn.__globals__, fn.__name__, fn.__defaults__, fn.__closure__)
    new_fn.__kwdefaults__ = fn.__kwdefaults__
    return new_fn


def hack_clanguage_output_templates():
    consts = []
    for v in CLanguage.output_templates.__code__.co_consts:
        if isinstance(v, str) and "static {impl_return_type}" in v:
            v = "Py_LOCAL_INLINE({impl_return_type})\n{c_basename}_impl({impl_parameters})\n"
        consts.append(v)
    CLanguage.output_templates = rebuild_func(CLanguage.output_templates, tuple(consts))


hack_clanguage_output_templates()


class Path_converter(CConverter):
    type = "PyObject *"
    converter = "PyUnicode_FSConverter"
    c_default = "NULL"
    typed = "Union[Path, str, bytes]"

    def cleanup(self):
        return f"Py_XDECREF({self.name});"


class cstring_converter(CConverter):
    type = "const char *"
    converter = "cstring_converter"
    c_default = "NULL"
    typed = "Union[str, bytes]"

    def converter_init(self, *, accept=None):
        if accept == {NoneType}:
            self.converter = "cstring_optional_converter"
            self.typed = "Optional[Union[str, bytes]]"
        elif accept is not None:
            fail("cstring_converter: illegal 'accept' argument " + repr(accept))


class ssize_t_converter(CConverter):
    type = "Py_ssize_t"
    converter = "ssize_t_converter"
    typed = "int"


class fd_converter(CConverter):
    type = "int"
    converter = "fd_converter"
    typed = "int"


class off_t_converter(CConverter):
    type = "Py_off_t"
    converter = "off_t_converter"
    typed = "int"


class inet_addr_converter(CConverter):
    type = "sockaddr_any"
    converter = "inet_addr_converter"
    impl_by_reference = True
    typed = "Tuple[str, int]"


class uid_t_converter(CConverter):
    type = "uid_t"
    converter = "uid_converter"
    typed = "int"


class gid_t_converter(CConverter):
    type = "gid_t"
    converter = "gid_converter"
    typed = "int"


class object_converter(object_converter):
    typed = "object"

    def converter_init(self, *, typed=None, **kwargs):
        self.typed = typed
        super().converter_init(**kwargs)


class object_return_converter(CReturnConverter):
    typed = "object"

    def return_converter_init(self, *, typed=None, **kwargs):
        self.typed = typed
        super().return_converter_init(**kwargs)


class None_return_converter(CReturnConverter):
    typed = "None"


class Any_return_converter(CReturnConverter):
    typed = "Any"


def main():
    clinic_main(sys.argv[1:])
    generate_readme()


if __name__ == "__main__":
    main()
