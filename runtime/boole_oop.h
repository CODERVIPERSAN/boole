/* Boole OOP + exceptions + modules (native). */
#ifndef BOOLE_OOP_H
#define BOOLE_OOP_H

#include "boole_rt.h"
#include <setjmp.h>

typedef struct BooleMethodEntry {
  const char *name;
  BooleNativeFn fn;
} BooleMethodEntry;

struct BooleClass {
  const char *name;
  const struct BooleClass *base;
  const BooleMethodEntry *methods;
  size_t nmethods;
};

BooleValue bv_class(const BooleClass *cls);
BooleValue bv_instance(const BooleClass *cls);
BooleValue bv_func(BooleNativeFn fn, const char *name);
BooleValue bv_module(const char *name);

const BooleClass *bv_as_class(BooleValue v);
BooleValue bv_call_value(BooleValue callee, int argc, BooleValue *argv);
BooleValue bv_call_method(BooleValue obj, const char *name, int argc, BooleValue *argv);

/* Exceptions via setjmp. Frame must be used with setjmp in the generated C. */
typedef struct BooleExcFrame {
  jmp_buf buf;
  char type[64];
  char msg[256];
  int raised;
} BooleExcFrame;

BooleExcFrame *bv_exc_push(void);
void bv_exc_pop(void);
void bv_raise(const char *type, const char *msg);
int bv_exc_match(const char *type);
void bv_exc_clear(void);
const char *bv_exc_type(void);
const char *bv_exc_msg(void);
void bv_exc_reraise(void);

/* Built-in modules */
BooleValue bv_mod_math(void);
BooleValue bv_mod_json(void);

#endif
