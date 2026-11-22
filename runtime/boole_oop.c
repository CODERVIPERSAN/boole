/* Boole OOP, exceptions, modules — native runtime. */
#define _POSIX_C_SOURCE 200809L
#include "boole_oop.h"

#include <math.h>
#include <string.h>

/* ---- retain/release hooks for new tags (also handled in boole_rt.c) ---- */

static BooleValue dict_get_cstr(BooleValue dict, const char *name) {
  BooleValue key = bv_str(name);
  BooleValue val = bv_dict_get(dict, key);
  bv_release(key);
  return val;
}

static void dict_set_cstr(BooleValue dict, const char *name, BooleValue value) {
  BooleValue key = bv_str(name);
  bv_dict_set(dict, key, value);
}

BooleValue bv_class(const BooleClass *cls) {
  BooleObj *o = (BooleObj *)calloc(1, sizeof(BooleObj));
  if (!o) bv_die("out of memory");
  o->tag = BV_CLASS;
  o->refs = 1;
  o->u.class_.cls = cls;
  BooleValue v;
  v.tag = BV_CLASS;
  v.as.obj = o;
  return v;
}

BooleValue bv_instance(const BooleClass *cls) {
  BooleObj *o = (BooleObj *)calloc(1, sizeof(BooleObj));
  if (!o) bv_die("out of memory");
  o->tag = BV_INSTANCE;
  o->refs = 1;
  o->u.instance.cls = cls;
  o->u.instance.fields = bv_dict();
  BooleValue v;
  v.tag = BV_INSTANCE;
  v.as.obj = o;
  return v;
}

BooleValue bv_func(BooleNativeFn fn, const char *name) {
  BooleObj *o = (BooleObj *)calloc(1, sizeof(BooleObj));
  if (!o) bv_die("out of memory");
  o->tag = BV_FUNC;
  o->refs = 1;
  o->u.func.fn = fn;
  o->u.func.name = name;
  BooleValue v;
  v.tag = BV_FUNC;
  v.as.obj = o;
  return v;
}

BooleValue bv_module(const char *name) {
  BooleObj *o = (BooleObj *)calloc(1, sizeof(BooleObj));
  if (!o) bv_die("out of memory");
  o->tag = BV_MODULE;
  o->refs = 1;
  o->u.module.name = strdup(name);
  o->u.module.attrs = bv_dict();
  BooleValue v;
  v.tag = BV_MODULE;
  v.as.obj = o;
  return v;
}

const BooleClass *bv_as_class(BooleValue v) {
  if (v.tag != BV_CLASS || !v.as.obj) bv_die("expected class");
  return v.as.obj->u.class_.cls;
}

static BooleNativeFn find_method(const BooleClass *cls, const char *name) {
  while (cls) {
    for (size_t i = 0; i < cls->nmethods; i++) {
      if (strcmp(cls->methods[i].name, name) == 0) return cls->methods[i].fn;
    }
    cls = cls->base;
  }
  return NULL;
}

BooleValue bv_call_value(BooleValue callee, int argc, BooleValue *argv) {
  if (callee.tag == BV_FUNC) {
    return callee.as.obj->u.func.fn(argc, argv);
  }
  if (callee.tag == BV_CLASS) {
    const BooleClass *cls = callee.as.obj->u.class_.cls;
    BooleValue inst = bv_instance(cls);
    BooleNativeFn init = find_method(cls, "__init__");
    if (init) {
      BooleValue *args = (BooleValue *)malloc(sizeof(BooleValue) * (size_t)(argc + 1));
      if (!args) bv_die("out of memory");
      args[0] = bv_retain(inst);
      for (int i = 0; i < argc; i++) args[i + 1] = argv[i];
      BooleValue r = init(argc + 1, args);
      bv_release(r);
      bv_release(args[0]);
      free(args);
    } else if (argc > 0) {
      bv_release(inst);
      bv_die("class takes no arguments");
    }
    return inst;
  }
  bv_die("object is not callable");
  return bv_none();
}

BooleValue bv_call_method(BooleValue obj, const char *name, int argc, BooleValue *argv) {
  if (obj.tag != BV_INSTANCE) bv_die("method call on non-instance");
  const BooleClass *cls = obj.as.obj->u.instance.cls;
  BooleNativeFn fn = find_method(cls, name);
  if (!fn) {
    char buf[128];
    snprintf(buf, sizeof(buf), "no method '%s'", name);
    bv_die(buf);
  }
  BooleValue *args = (BooleValue *)malloc(sizeof(BooleValue) * (size_t)(argc + 1));
  if (!args) bv_die("out of memory");
  args[0] = bv_retain(obj);
  for (int i = 0; i < argc; i++) args[i + 1] = argv[i];
  BooleValue r = fn(argc + 1, args);
  bv_release(args[0]);
  free(args);
  return r;
}

/* ---- exceptions ---- */

#define BOOLE_MAX_EXC 64
static BooleExcFrame boole_exc_stack[BOOLE_MAX_EXC];
static int boole_exc_sp = -1;
static char boole_exc_type_buf[64];
static char boole_exc_msg_buf[256];
static int boole_exc_pending = 0;

BooleExcFrame *bv_exc_push(void) {
  if (boole_exc_sp + 1 >= BOOLE_MAX_EXC) bv_die("exception stack overflow");
  boole_exc_sp++;
  BooleExcFrame *f = &boole_exc_stack[boole_exc_sp];
  f->raised = 0;
  f->type[0] = 0;
  f->msg[0] = 0;
  return f;
}

void bv_exc_pop(void) {
  if (boole_exc_sp >= 0) boole_exc_sp--;
}

void bv_raise(const char *type, const char *msg) {
  if (!type) type = "RuntimeError";
  if (!msg) msg = "";
  strncpy(boole_exc_type_buf, type, sizeof(boole_exc_type_buf) - 1);
  boole_exc_type_buf[sizeof(boole_exc_type_buf) - 1] = 0;
  strncpy(boole_exc_msg_buf, msg, sizeof(boole_exc_msg_buf) - 1);
  boole_exc_msg_buf[sizeof(boole_exc_msg_buf) - 1] = 0;
  boole_exc_pending = 1;
  if (boole_exc_sp < 0) {
    fprintf(stderr, "boole: %s: %s\n", type, msg);
    exit(1);
  }
  BooleExcFrame *f = &boole_exc_stack[boole_exc_sp];
  strncpy(f->type, type, sizeof(f->type) - 1);
  strncpy(f->msg, msg, sizeof(f->msg) - 1);
  f->raised = 1;
  longjmp(f->buf, 1);
}

int bv_exc_match(const char *type) {
  if (!boole_exc_pending) return 0;
  if (!type || strcmp(type, "Exception") == 0) return 1;
  /* ZeroDivisionError matches Exception; Exact name match otherwise. */
  if (strcmp(boole_exc_type_buf, type) == 0) return 1;
  return 0;
}

void bv_exc_clear(void) { boole_exc_pending = 0; }

const char *bv_exc_type(void) { return boole_exc_type_buf; }
const char *bv_exc_msg(void) { return boole_exc_msg_buf; }

void bv_exc_reraise(void) {
  if (!boole_exc_pending) return;
  if (boole_exc_sp < 0) {
    fprintf(stderr, "boole: %s: %s\n", boole_exc_type_buf, boole_exc_msg_buf);
    exit(1);
  }
  BooleExcFrame *f = &boole_exc_stack[boole_exc_sp];
  strncpy(f->type, boole_exc_type_buf, sizeof(f->type) - 1);
  strncpy(f->msg, boole_exc_msg_buf, sizeof(f->msg) - 1);
  f->raised = 1;
  longjmp(f->buf, 1);
}

/* ---- builtin modules ---- */

static BooleValue math_sqrt(int argc, BooleValue *argv) {
  if (argc < 1) bv_die("sqrt() missing argument");
  return bv_float(sqrt(bv_as_float(argv[0])));
}

static BooleValue math_sin(int argc, BooleValue *argv) {
  if (argc < 1) bv_die("sin() missing argument");
  return bv_float(sin(bv_as_float(argv[0])));
}

static BooleValue math_cos(int argc, BooleValue *argv) {
  if (argc < 1) bv_die("cos() missing argument");
  return bv_float(cos(bv_as_float(argv[0])));
}

static BooleValue math_floor(int argc, BooleValue *argv) {
  if (argc < 1) bv_die("floor() missing argument");
  return bv_float(floor(bv_as_float(argv[0])));
}

BooleValue bv_mod_math(void) {
  BooleValue m = bv_module("math");
  dict_set_cstr(m.as.obj->u.module.attrs, "sqrt", bv_func(math_sqrt, "sqrt"));
  dict_set_cstr(m.as.obj->u.module.attrs, "sin", bv_func(math_sin, "sin"));
  dict_set_cstr(m.as.obj->u.module.attrs, "cos", bv_func(math_cos, "cos"));
  dict_set_cstr(m.as.obj->u.module.attrs, "floor", bv_func(math_floor, "floor"));
  dict_set_cstr(m.as.obj->u.module.attrs, "pi", bv_float(3.141592653589793));
  return m;
}

BooleValue bv_mod_json(void) {
  /* Minimal stub module object; dumps/loads not fully ported yet. */
  return bv_module("json");
}

/* Override weak getattr/setattr from boole_rt.c by providing real ones —
   boole_rt.c still has stubs; we replace those functions there instead. */
