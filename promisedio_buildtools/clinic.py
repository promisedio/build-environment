import re
import sys
from . import cpp

sys.modules["cpp"] = sys.modules["promisedio_buildtools.cpp"]

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


_CLanguage_docstring_for_c_string = CLanguage.docstring_for_c_string
_CLanguage_output_templates = CLanguage.output_templates


def CLanguage_docstring_for_c_string(self, f):
    result = _CLanguage_docstring_for_c_string(self, f)
    module = readme_contents.setdefault(f.module.name, {"classes": {}, "functions": {}})
    if f.cls:
        module["classes"].setdefault(f.cls.name, {})[f.name] = f
    else:
        module["functions"][f.name] = f
    return result


def CLanguage_output_templates(self, f):
    result = _CLanguage_output_templates(self, f)
    result["impl_definition"] = result["impl_definition"].replace(
        "static {impl_return_type}",
        "Py_LOCAL_INLINE({impl_return_type})"
    )
    result["impl_prototype"] = result["impl_prototype"].replace(
        "static {impl_return_type}",
        "Py_LOCAL_INLINE({impl_return_type})"
    )
    new_or_init = f.kind in (METHOD_NEW, METHOD_INIT)
    if new_or_init:
        converters = [p.converter for p in f.render_parameters]
        for converter in converters:
            if isinstance(converter, self_converter) and converter.specified_context:
                result["parser_definition"] = result["parser_definition"].replace(
                    "{initializers}",
                    "{context_init}\n    {initializers}"
                )
                result["impl_definition"] = result["impl_definition"].replace(
                    "{impl_parameters}",
                    "_ctx_var, {impl_parameters}"
                )
                result["impl_prototype"] = result["impl_prototype"].replace(
                    "{impl_parameters}",
                    "_ctx_var, {impl_parameters}"
                )
                result["parser_definition"] = result["parser_definition"].replace(
                    "{impl_arguments}",
                    "_ctx, {impl_arguments}"
                )
                break
    return result


CLanguage.docstring_for_c_string = CLanguage_docstring_for_c_string
CLanguage.output_templates = CLanguage_output_templates


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


class self_converter(self_converter):
    def converter_init(self, *, type=None, context=None):
        super().converter_init(type=type)
        self.specified_context = context

    def set_template_dict(self, template_dict):
        super().set_template_dict(template_dict)
        if self.specified_context:
            template_dict["context_init"] = "{};".format(self.specified_context);


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


class Any_return_converter(CReturnConverter):
    typed = "Any"


class bool_return_converter(bool_return_converter):
    typed = "bool"


class Py_ssize_t_return_converter(Py_ssize_t_return_converter):
    typed = "int"


def generate_readme():

    def replacer(m):
        name = m.group(1)
        if name in functions or name in classes:
            return f"[{name}](#{name.lower()})"
        return f"`{name}`"

    def generate_descr(name, f):
        args = [get_parameter_annotation(p) for p in list(f.parameters.values())[1:]]
        returns = get_return_annotation(f)
        output.append("```python")
        output.append(f"{name}({', '.join(args)}) -> {returns}")
        output.append("```")
        _, doc = f.docstring.split("--", 1)
        doc = doc.strip()
        doc = re.sub(r"`([^`]*)`", replacer, doc)
        output.append(doc)
        output.append("")

    def generate_function(name, f):
        output.append(f"#### {name}")
        generate_descr(name, f)

    for module in sorted(readme_contents):
        template = open("README.md").read()
        pattern = rf"<!---\s*template:\[{module}\]\s*([\S\s]*?)(?=-->)-->[\s\S]*<!---\s*end:\[{module}\]\s*-->"
        match = re.search(pattern, template)
        if not match:
            print(f"<!--- template:[{module}] --> missing")
            continue
        sorted_classes = match.group(1).split()
        output = []
        classes = readme_contents[module]["classes"]
        functions = readme_contents[module]["functions"]
        output.append(f"# {module} module")
        for function in sorted(functions):
            generate_function(function, functions[function])
        for cls in (sorted_classes + sorted(set(classes) - set(sorted_classes))):
            if cls not in classes:
                print(f"Unknown class {cls}")
            output.append(f"### {cls}")
            functions = classes[cls]
            new_func = functions.pop("__new__", None)
            if new_func:
                generate_descr(f"{cls}", new_func)
            for function in sorted(functions):
                generate_function(f"{cls}.{function}", functions[function])
        output.append("")

        def repl(m):
            items = "\n".join(m.group(1).split())
            out = ""
            if items:
                out += f"<!--- template:[{module}]\n{items}\n-->\n"
            else:
                out += f"<!--- template:[{module}] -->\n"
            return (
                out +
                "\n".join(output) +
                f"\n<!--- end:[{module}] -->"
            )

        result = re.sub(pattern, repl, template, 1, re.MULTILINE)
        if result != template:
            open("README.md", "wt").write(result)


def main():
    clinic_main(sys.argv[1:])
    generate_readme()


if __name__ == "__main__":
    main()
