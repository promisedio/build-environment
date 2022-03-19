// Copyright (c) 2021-2022 Andrey Churin <aachurin@gmail.com> Promisedio

#ifndef PROMISEDIO_CAPSULE_H
#define PROMISEDIO_CAPSULE_H

#include "_promisedio/base.h"
#include "_promisedio/memory.h"
#include "_promisedio/module.h"


Py_LOCAL_INLINE(void *)
Capsule_Load(PyObject *module, const char *api_id)
{
    if (!module) {
        PyErr_Format(PyExc_ImportError, "could not import \"%s\"", api_id);
        return NULL;
    }
    PyObject *object = PyObject_GetAttrString(module, api_id);
    if (!object) {
        return NULL;
    }
    if (PyCapsule_GetContext(object) != _CTX__getmodule(module)) {
        PyErr_Format(PyExc_ImportError, "capsule \"%s\" is not valid", api_id);
        Py_DECREF(object);
        return NULL;
    }
    void *return_value = PyCapsule_GetPointer(object, api_id);
    Py_DECREF(object);
    return return_value;
}

#define Capsule_CREATE(module, api_id, export)                                              \
    do {                                                                                    \
        static void *c_api[] = export;                                                      \
        PyObject *_api = PyCapsule_New(&(c_api), STRINGIFY(api_id), NULL);                  \
        PyCapsule_SetContext(_api, _CTX__getmodule(module));                                \
        if (PyModule_AddObject(module, STRINGIFY(api_id), _api) < 0) {                      \
            Py_XDECREF(_api);                                                               \
            return -1;                                                                      \
        }                                                                                   \
    } while(0)

#define Capsule_MOUNT(api_id)                                                               \
    PyObject *CAT(api_id,__MODULE);                                                         \
    void *CAT(api_id,__CTX);

#define Capsule_VISIT(api_id) Py_VISIT(_ctx->CAT(api_id,__MODULE))
#define Capsule_CLEAR(api_id) Py_CLEAR(_ctx->CAT(api_id,__MODULE))

#define Capsule_LOAD(module_name, api_id)                                                   \
    do {                                                                                    \
        PyObject *_module = PyImport_ImportModule(module_name);                             \
        void *_api = Capsule_Load(_module, STRINGIFY(api_id));                              \
        if (!_api) {                                                                        \
            Py_XDECREF(_module);                                                            \
            return -1;                                                                      \
        }                                                                                   \
        _ctx->CAT(api_id,__MODULE) = _module;                                               \
        _ctx->CAT(api_id,__CTX) = _CTX__getmodule(_module);                                 \
        if (!CAT(api_id,__LOADED)) {                                                        \
            CAT(api_id,__LOADED) = 1;                                                       \
            memcpy(CAT(api_id,__API), _api, sizeof(CAT(api_id, __API)));                    \
        }                                                                                   \
    } while (0)

Py_LOCAL_INLINE(void *)
Capsule_GetFunc(const char *module_name, const char *api_id, int func_id)
{
    PyObject *_module = PyImport_ImportModule(module_name);
    void *ret = NULL;
    void **_api = Capsule_Load(_module, api_id);
    if (_api) {
        ret = _api[func_id];
    }
    Py_XDECREF(_module);
    return ret;
}

#define Capsule_GetFunc(module_name, api_id, func_id) Capsule_GetFunc(module_name, STRINGIFY(api_id), func_id)
#define CAPSULE_API(op) static op

#endif
