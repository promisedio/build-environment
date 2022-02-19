// Copyright (c) 2021-2022 Andrey Churin <aachurin@gmail.com> Promisedio

#ifndef PROMISEDIO_CONVERTERS_STRING_H
#define PROMISEDIO_CONVERTERS_STRING_H

Py_LOCAL_INLINE(int)
cstring_converter(PyObject *arg, const char **addr)
{
    Py_ssize_t size;
    const char *ret;
    if (PyUnicode_Check(arg)) {
        ret = PyUnicode_AsUTF8AndSize(arg, &size);
        if (ret == NULL)
            return 0;
    } else if (PyBytes_Check(arg)) {
        ret = PyBytes_AS_STRING(arg);
        size = PyBytes_GET_SIZE(arg);
    } else {
        PyErr_SetString(PyExc_TypeError,
                        "str or bytes expected");
        return 0;
    }
    if (strlen(ret) != (size_t) size) {
        PyErr_SetString(PyExc_ValueError,
                        "embedded null character");
        return 0;
    }
    *addr = ret;
    return 1;
}

Py_LOCAL_INLINE(int)
cstring_optional_converter(PyObject *arg, const char **addr)
{
    if (arg == Py_None) {
        *addr = NULL;
        return 1;
    }
    return cstring_converter(arg, addr);
}

#endif
