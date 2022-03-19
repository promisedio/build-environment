// Copyright (c) 2021-2022 Andrey Churin <aachurin@gmail.com> Promisedio

#ifndef PROMISEDIO_MEMORY_H
#define PROMISEDIO_MEMORY_H

#include "_promisedio/base.h"

#ifdef BUILD_DEBUG_MEM
Py_LOCAL_INLINE(void *)
Py_Malloc(size_t n)
{
    void *ptr = PyMem_Malloc(n);
    MEMLOG("Malloc", ptr, "RAW");
    return ptr;
}

Py_LOCAL_INLINE(void)
Py_Free(void *op)
{
    MEMLOG("Free", op, "RAW");
    PyMem_Free(op);
}

Py_LOCAL_INLINE(PyObject *)
Py_New(PyTypeObject *tp)
{
    PyObject *ptr = _PyObject_New(tp);
    MEMLOG("New", ptr, Py_TYPE(ptr)->tp_name);
    return ptr;
}

Py_LOCAL_INLINE(PyObject *)
Py_GC_New(PyTypeObject *tp)
{
    PyObject *ptr = _PyObject_GC_New(tp);
    MEMLOG("New", ptr, Py_TYPE(ptr)->tp_name);
    return ptr;
}

Py_LOCAL_INLINE(void)
Py_Delete(void *op)
{
    MEMLOG("Delete", op, Py_TYPE(op)->tp_name);
    PyMem_Free(op);
}

Py_LOCAL_INLINE(void)
Py_GC_Delete(void *op)
{
    MEMLOG("Delete", op, Py_TYPE(op)->tp_name);
    PyObject_GC_Del(op);
}

#define PyTrack_DECREF(op)                                  \
do {                                                        \
    PyObject *_tmp = _PyObject_CAST(op);                    \
    MEMLOG("Decref", _tmp, Py_TYPE(_tmp)->tp_name);         \
    Py_DECREF(_tmp);                                        \
} while (0)

#define PyTrack_XDECREF(op)                                 \
do {                                                        \
    PyObject *_tmp1 = _PyObject_CAST(op);                   \
    if (_tmp1 != NULL) {                                    \
        PyTrack_DECREF(_tmp1);                              \
    }                                                       \
} while (0)

#define PyTrack_INCREF(op)                                  \
do {                                                        \
    PyObject *_tmp = _PyObject_CAST(op);                    \
    MEMLOG("Incref", _tmp, Py_TYPE(_tmp)->tp_name);         \
    Py_INCREF(_tmp);                                        \
} while (0)

#define PyTrack_XINCREF(op)                                 \
do {                                                        \
    PyObject *_tmp1 = _PyObject_CAST(op);                   \
    if (_tmp1 != NULL) {                                    \
        PyTrack_INCREF(_tmp1);                              \
    }                                                       \
} while (0)

#define PyTrack_CLEAR(op)                                   \
do {                                                        \
    PyObject *_tmp1 = _PyObject_CAST(op);                   \
    if (_tmp1 != NULL) {                                    \
        (op) = NULL;                                        \
        PyTrack_DECREF(_tmp1);                              \
    }                                                       \
} while (0)

#define PyTrack_SETREF(op, op2)                             \
do {                                                        \
    PyObject *_tmp1 = _PyObject_CAST(op);                   \
    (op) = (op2);                                           \
    PyTrack_DECREF(_tmp1);                                  \
} while (0)

#define PyTrack_XSETREF(op, op2)                            \
do {                                                        \
    PyObject *_tmp2 = _PyObject_CAST(op);                   \
    (op) = (op2);                                           \
    PyTrack_XDECREF(_tmp2);                                 \
} while (0)

#define PyTrack_ENTER(op)                                   \
do {                                                        \
    PyObject *_tmp = _PyObject_CAST(op);                    \
    MEMLOG("Enter", _tmp, Py_TYPE(_tmp)->tp_name);          \
} while (0)

#define PyTrack_RESIZE(op)                                  \
do {                                                        \
    PyObject *_tmp = _PyObject_CAST(op);                    \
    MEMLOG("Resize", _tmp, Py_TYPE(_tmp)->tp_name);         \
} while (0)

#define PyTrack_RESIZED(op)                                 \
do {                                                        \
    PyObject *_tmp = _PyObject_CAST(op);                    \
    MEMLOG("Resized", _tmp,  Py_TYPE(_tmp)->tp_name);       \
} while (0)

#define PyTrack_NEW(op)                                     \
do {                                                        \
    PyObject *_tmp = _PyObject_CAST(op);                    \
    MEMLOG("New", _tmp, Py_TYPE(_tmp)->tp_name);            \
} while (0)

#define PyTrack_DELETE(op)                                  \
do {                                                        \
    PyObject *_tmp = _PyObject_CAST(op);                    \
    MEMLOG("Delete", _tmp, Py_TYPE(_tmp)->tp_name);         \
} while (0)

#else

#define Py_Malloc PyMem_Malloc
#define Py_Free PyMem_Free
#define Py_New _PyObject_New
#define Py_Delete PyMem_Free
#define Py_GC_New _PyObject_GC_New
#define Py_GC_Delete PyObject_GC_Del
#define PyTrack_DECREF Py_DECREF
#define PyTrack_XDECREF Py_XDECREF
#define PyTrack_INCREF Py_INCREF
#define PyTrack_XINCREF Py_XINCREF
#define PyTrack_CLEAR Py_CLEAR
#define PyTrack_SETREF Py_SETREF
#define PyTrack_XSETREF Py_XSETREF
#define PyTrack_ENTER(op)
#define PyTrack_RESIZE(op)
#define PyTrack_RESIZED(op)
#define PyTrack_NEW(op)
#define PyTrack_DELETE(op)

#endif

#ifndef BUILD_DISABLE_FREELISTS

typedef struct {
    void *ptr;
    Py_ssize_t size;
    Py_ssize_t limit;
} freelist_gc_info;

typedef struct {
    void *ptr;
    Py_ssize_t size;
    Py_ssize_t limit;
} freelist_info;

typedef struct {
    void *ptr;
    Py_ssize_t size;
    Py_ssize_t limit;
    size_t obj_size;
} freelist_raw_info;

#define Freelist_Raw(name) freelist_raw_info name##__raw_freelist;
#define Freelist(name) freelist_info name##__freelist;
#define Freelist_GC(name) freelist_gc_info name##__gc_freelist;

#define Freelist_Raw_Init(name, maxsize) \
_ctx->name##__raw_freelist =             \
    (freelist_raw_info) {                \
    .size=0,                             \
    .ptr=NULL,                           \
    .limit=(maxsize),                    \
    .obj_size=sizeof(name)               \
}

#define Freelist_Init(name, maxsize) \
_ctx->name##__freelist =             \
    (freelist_info) {                \
    .ptr=NULL,                           \
    .size=0,                             \
    .limit=(maxsize)                     \
}

#define Freelist_GC_Init(name, maxsize) \
_ctx->name##__gc_freelist =             \
    (freelist_gc_info) {                \
    .ptr=NULL,                          \
    .size=0,                            \
    .limit=(maxsize)                    \
}

#define Freelist_CLEAR(fl, dealloc)     \
    void *next, *ptr = (fl)->ptr;       \
    while (ptr) {                       \
        next = *((void **) ptr);        \
        dealloc(ptr);                   \
        ptr = next;                     \
    }                                   \
    (fl)->size = 0;

Py_LOCAL_INLINE(void)
Freelist_Raw_Clear(freelist_raw_info *fl)
{
    Freelist_CLEAR(fl, PyMem_Free)
}

Py_LOCAL_INLINE(void)
Freelist_Clear(freelist_info *fl)
{
    Freelist_CLEAR(fl, PyMem_Free)
}

Py_LOCAL_INLINE(void)
Freelist_GC_Clear(freelist_gc_info *fl)
{
    Freelist_CLEAR(fl, PyObject_GC_Del)
}

#define Freelist_Raw_Clear(name) Freelist_Raw_Clear(&(_ctx->name##__raw_freelist))
#define Freelist_Clear(name) Freelist_Clear(&(_ctx->name##__freelist))
#define Freelist_GC_Clear(name) Freelist_GC_Clear(&(_ctx->name##__gc_freelist))

Py_LOCAL_INLINE(void *)
freelist__pop(freelist_raw_info *fl)
{
    void *ptr = fl->ptr;
    if (ptr) {
        fl->ptr = *((void **) ptr);
        --fl->size;
    }
    return ptr;
}

Py_LOCAL_INLINE(void)
freelist__push(freelist_raw_info *fl, void *ptr)
{
    *((void **) ptr) = fl->ptr;
    fl->ptr = ptr;
    ++fl->size;
}

Py_LOCAL_INLINE(void *)
Freelist_Malloc(freelist_raw_info *fl)
{
    void *ptr = freelist__pop(fl);
    if (!ptr) {
        ptr = PyMem_Malloc(fl->obj_size);
    }
    MEMLOG("Malloc", ptr, "RAW");
    return ptr;
}

#define Freelist_Malloc(name) Freelist_Malloc(&_ctx->name##__raw_freelist)

Py_LOCAL_INLINE(void)
Freelist_Free(freelist_raw_info *fl, void *ptr)
{
    MEMLOG("Free", ptr, "RAW");
    if (fl->size >= fl->limit) {
        PyMem_Free(ptr);
    } else {
        freelist__push(fl, ptr);
    }
}

#define Freelist_Free(name, ptr) Freelist_Free(&_ctx->name##__raw_freelist, ptr)

Py_LOCAL_INLINE(PyObject *)
Freelist_New(freelist_info *fl, PyTypeObject *tp)
{
    void *ptr = freelist__pop((freelist_raw_info *) fl);
    if (ptr) {
        PyObject_Init(ptr, tp);
    } else {
        ptr = _PyObject_New(tp);
    }
    MEMLOG("New", ptr, Py_TYPE(ptr)->tp_name);
    return (PyObject *) ptr;
}

#define Freelist_New(name) Freelist_New(&_ctx->name##__freelist)

Py_LOCAL_INLINE(void)
Freelist_Delete(freelist_info *fl, PyObject *obj)
{
    MEMLOG("Delete", obj, Py_TYPE(obj)->tp_name);
    if (fl->size >= fl->limit) {
        PyMem_Free(obj);
    } else {
        freelist__push((freelist_raw_info *) fl, obj);
    }
}

#define Freelist_Delete(name, ob) Freelist_Delete(&_ctx->name##__freelist, _PyObject_CAST(ob))

Py_LOCAL_INLINE(PyObject *)
Freelist_GC_New(freelist_gc_info *fl, PyTypeObject *tp)
{
    void *ptr = freelist__pop((freelist_raw_info *) fl);
    if (ptr) {
        PyObject_Init(ptr, tp);
    } else {
        ptr = _PyObject_GC_New(tp);
    }
    MEMLOG("New", ptr, Py_TYPE(ptr)->tp_name);
    return (PyObject *) ptr;
}

#define Freelist_GC_New(name) Freelist_GC_New(&_ctx->name##__gc_freelist, _ctx->name)

Py_LOCAL_INLINE(void)
Freelist_GC_Delete(freelist_gc_info *fl, PyObject *obj)
{
    MEMLOG("Delete", obj, Py_TYPE(obj)->tp_name);
    if (fl->size >= fl->limit) {
        PyObject_GC_Del(obj);
    } else {
        freelist__push((freelist_raw_info *) fl, obj);
    }
}

#define Freelist_GC_Delete(name, ob) Freelist_GC_Delete(&_ctx->name##__gc_freelist, _PyObject_CAST(ob))

#define Freelist_GC_Limit(name, value) (&(_ctx->name##__gc_freelist))->limit = (value)
#define Freelist_Limit(name, value) (&(_ctx->name##__freelist))->limit = (value)
#define Freelist_Raw_Limit(name, value) (&(_ctx->name##__raw_freelist))->limit = (value)

#else

#define TOUCH(x) (void)(x)

#define Freelist_Raw(name) size_t name##__raw_freelist;
#define Freelist(name)
#define Freelist_GC(name)

#define Freelist_Raw_Init(name, maxsize) _ctx->name##__raw_freelist = sizeof(name)
#define Freelist_Init(name, maxsize) TOUCH(_ctx)
#define Freelist_GC_Init(name, maxsize) TOUCH(_ctx)

#define Freelist_Malloc(name) Py_Malloc(_ctx->name##__raw_freelist)
#define Freelist_Free(name, ptr) Py_Free(ptr), TOUCH(_ctx)
#define Freelist_New(name) Py_New(_ctx->name)
#define Freelist_Delete(name, obj) Py_Delete(obj), TOUCH(_ctx)
#define Freelist_GC_New(name) Py_GC_New(_ctx->name)
#define Freelist_GC_Delete(name, obj) Py_GC_Delete(obj), TOUCH(_ctx)

#define Freelist_GC_Clear(name) TOUCH(_ctx)
#define Freelist_Clear(name) TOUCH(_ctx)
#define Freelist_Raw_Clear(name) TOUCH(_ctx)

#define Freelist_GC_Limit(name, value) TOUCH(_ctx)
#define Freelist_Limit(name, value) TOUCH(_ctx)
#define Freelist_Raw_Limit(name, value) TOUCH(_ctx)

#endif

#endif
