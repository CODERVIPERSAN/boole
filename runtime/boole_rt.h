/* Boole native runtime v0.1 — tagged values, reference counted. */
#ifndef BOOLE_RT_H
#define BOOLE_RT_H

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef enum {
  BV_NONE = 0,
  BV_BOOL,
  BV_INT,
  BV_FLOAT,
  BV_STR,
  BV_LIST,
  BV_DICT,
  BV_CLASS,
  BV_INSTANCE,
  BV_FUNC,
  BV_MODULE
} BooleTag;

typedef struct BooleObj BooleObj;
typedef struct BooleClass BooleClass;

typedef struct {
  BooleTag tag;
  union {
    bool b;
    int64_t i;
    double f;
    BooleObj *obj;
  } as;
} BooleValue;

typedef BooleValue (*BooleNativeFn)(int argc, BooleValue *argv);

struct BooleObj {
  BooleTag tag;
  int refs;
  union {
    struct {
      char *data;
      size_t len;
    } str;
    struct {
      BooleValue *items;
      size_t len;
      size_t cap;
    } list;
    struct {
      BooleValue *keys;
      BooleValue *vals;
      size_t len;
      size_t cap;
    } dict;
    struct {
      const BooleClass *cls;
    } class_;
    struct {
      const BooleClass *cls;
      BooleValue fields; /* dict */
    } instance;
    struct {
      BooleNativeFn fn;
      const char *name;
    } func;
    struct {
      char *name;
      BooleValue attrs; /* dict */
    } module;
  } u;
};

BooleValue bv_none(void);
BooleValue bv_bool(bool v);
BooleValue bv_int(int64_t v);
BooleValue bv_float(double v);
BooleValue bv_str(const char *s);
BooleValue bv_str_n(const char *s, size_t n);
BooleValue bv_list(void);
BooleValue bv_dict(void);

BooleValue bv_retain(BooleValue v);
void bv_release(BooleValue v);

bool bv_truthy(BooleValue v);
int64_t bv_as_int(BooleValue v);
double bv_as_float(BooleValue v);
const char *bv_as_cstr(BooleValue v);

BooleValue bv_add(BooleValue a, BooleValue b);
BooleValue bv_sub(BooleValue a, BooleValue b);
BooleValue bv_mul(BooleValue a, BooleValue b);
BooleValue bv_div(BooleValue a, BooleValue b);
BooleValue bv_floordiv(BooleValue a, BooleValue b);
BooleValue bv_mod(BooleValue a, BooleValue b);
BooleValue bv_pow(BooleValue a, BooleValue b);
BooleValue bv_neg(BooleValue a);

bool bv_eq(BooleValue a, BooleValue b);
bool bv_lt(BooleValue a, BooleValue b);
bool bv_le(BooleValue a, BooleValue b);
bool bv_gt(BooleValue a, BooleValue b);
bool bv_ge(BooleValue a, BooleValue b);

void bv_list_push(BooleValue list, BooleValue item);
BooleValue bv_list_get(BooleValue list, BooleValue index);
void bv_list_set(BooleValue list, BooleValue index, BooleValue item);
BooleValue bv_list_slice(BooleValue list, BooleValue start, BooleValue stop);
BooleValue bv_slice(BooleValue obj, BooleValue start, BooleValue stop);
void bv_dict_set(BooleValue dict, BooleValue key, BooleValue value);
BooleValue bv_dict_get(BooleValue dict, BooleValue key);
BooleValue bv_index_get(BooleValue obj, BooleValue index);
void bv_index_set(BooleValue obj, BooleValue index, BooleValue value);

BooleValue bv_call_print(int argc, BooleValue *argv);
BooleValue bv_call_len(BooleValue v);
BooleValue bv_call_range(int argc, BooleValue *argv);
BooleValue bv_call_str(BooleValue v);
BooleValue bv_call_int(BooleValue v);
BooleValue bv_call_float(BooleValue v);
BooleValue bv_call_bool(BooleValue v);
BooleValue bv_call_sorted(BooleValue v);
BooleValue bv_call_max(int argc, BooleValue *argv);
BooleValue bv_call_min(int argc, BooleValue *argv);
BooleValue bv_call_sum(BooleValue v);
BooleValue bv_call_abs(BooleValue v);
BooleValue bv_call_type(BooleValue v);

BooleValue bv_getattr(BooleValue obj, const char *name);
void bv_setattr(BooleValue obj, const char *name, BooleValue value);

char *bv_format(BooleValue v);
void bv_die(const char *msg);

#endif
