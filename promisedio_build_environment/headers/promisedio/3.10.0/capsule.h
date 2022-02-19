#ifndef HEADER_CAPSULE_H
#define HEADER_CAPSULE_H

typedef struct {
    PyObject_HEAD
    void *pointer;
    const char *name;
    void *context;
    PyCapsule_Destructor destructor;
} PyCapsule;

#endif