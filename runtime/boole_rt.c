/* Boole native runtime v0.1 — refcounted tagged values (memory-safe for users). */
#define _POSIX_C_SOURCE 200809L
#include "boole_rt.h"
#include "boole_oop.h"

#include <math.h>
#include <string.h>

void bv_die(const char *msg) {
  fprintf(stderr, "boole: %s\n", msg);
  exit(1);
}

static char *bv_xstrdup(const char *s) {
  size_t n = strlen(s);
  char *out = (char *)malloc(n + 1);
  if (!out) bv_die("out of memory");
  memcpy(out, s, n + 1);
  return out;
}

static BooleObj *obj_new(BooleTag tag) {
  BooleObj *o = (BooleObj *)calloc(1, sizeof(BooleObj));
  if (!o) bv_die("out of memory");
  o->tag = tag;
  o->refs = 1;
  return o;
}

BooleValue bv_none(void) {
  BooleValue v;
  v.tag = BV_NONE;
  v.as.i = 0;
  return v;
}

BooleValue bv_bool(bool v) {
  BooleValue r;
  r.tag = BV_BOOL;
  r.as.b = v;
  return r;
}

BooleValue bv_int(int64_t v) {
  BooleValue r;
  r.tag = BV_INT;
  r.as.i = v;
  return r;
}

BooleValue bv_float(double v) {
  BooleValue r;
  r.tag = BV_FLOAT;
  r.as.f = v;
  return r;
}

BooleValue bv_str_n(const char *s, size_t n) {
  BooleObj *o = obj_new(BV_STR);
  o->u.str.data = (char *)malloc(n + 1);
  if (!o->u.str.data) bv_die("out of memory");
  memcpy(o->u.str.data, s, n);
  o->u.str.data[n] = 0;
  o->u.str.len = n;
  BooleValue v;
  v.tag = BV_STR;
  v.as.obj = o;
  return v;
}

BooleValue bv_str(const char *s) { return bv_str_n(s, strlen(s)); }

BooleValue bv_list(void) {
  BooleObj *o = obj_new(BV_LIST);
  o->u.list.items = NULL;
  o->u.list.len = 0;
  o->u.list.cap = 0;
  BooleValue v;
  v.tag = BV_LIST;
  v.as.obj = o;
  return v;
}

BooleValue bv_dict(void) {
  BooleObj *o = obj_new(BV_DICT);
  o->u.dict.keys = NULL;
  o->u.dict.vals = NULL;
  o->u.dict.len = 0;
  o->u.dict.cap = 0;
  BooleValue v;
  v.tag = BV_DICT;
  v.as.obj = o;
  return v;
}

static int is_heap(BooleTag t) {
  return t == BV_STR || t == BV_LIST || t == BV_DICT || t == BV_CLASS || t == BV_INSTANCE ||
         t == BV_FUNC || t == BV_MODULE;
}

BooleValue bv_retain(BooleValue v) {
  if (is_heap(v.tag) && v.as.obj) v.as.obj->refs++;
  return v;
}

static void obj_free(BooleObj *o) {
  if (!o) return;
  if (o->tag == BV_STR) {
    free(o->u.str.data);
  } else if (o->tag == BV_LIST) {
    for (size_t i = 0; i < o->u.list.len; i++) bv_release(o->u.list.items[i]);
    free(o->u.list.items);
  } else if (o->tag == BV_DICT) {
    for (size_t i = 0; i < o->u.dict.len; i++) {
      bv_release(o->u.dict.keys[i]);
      bv_release(o->u.dict.vals[i]);
    }
    free(o->u.dict.keys);
    free(o->u.dict.vals);
  } else if (o->tag == BV_INSTANCE) {
    bv_release(o->u.instance.fields);
  } else if (o->tag == BV_MODULE) {
    free(o->u.module.name);
    bv_release(o->u.module.attrs);
  }
  free(o);
}

void bv_release(BooleValue v) {
  if (!is_heap(v.tag) || !v.as.obj) return;
  v.as.obj->refs--;
  if (v.as.obj->refs <= 0) obj_free(v.as.obj);
}

bool bv_truthy(BooleValue v) {
  switch (v.tag) {
    case BV_NONE: return false;
    case BV_BOOL: return v.as.b;
    case BV_INT: return v.as.i != 0;
    case BV_FLOAT: return v.as.f != 0.0;
    case BV_STR: return v.as.obj->u.str.len != 0;
    case BV_LIST: return v.as.obj->u.list.len != 0;
    case BV_DICT: return v.as.obj->u.dict.len != 0;
    case BV_CLASS:
    case BV_INSTANCE:
    case BV_FUNC:
    case BV_MODULE: return true;
  }
  return false;
}

int64_t bv_as_int(BooleValue v) {
  if (v.tag == BV_INT) return v.as.i;
  if (v.tag == BV_BOOL) return v.as.b ? 1 : 0;
  if (v.tag == BV_FLOAT) return (int64_t)v.as.f;
  bv_die("expected int");
  return 0;
}

double bv_as_float(BooleValue v) {
  if (v.tag == BV_FLOAT) return v.as.f;
  if (v.tag == BV_INT) return (double)v.as.i;
  if (v.tag == BV_BOOL) return v.as.b ? 1.0 : 0.0;
  bv_die("expected float");
  return 0;
}

const char *bv_as_cstr(BooleValue v) {
  if (v.tag != BV_STR) bv_die("expected str");
  return v.as.obj->u.str.data;
}

char *bv_format(BooleValue v) {
  char buf[64];
  switch (v.tag) {
    case BV_NONE: return bv_xstrdup("None");
    case BV_BOOL: return bv_xstrdup(v.as.b ? "True" : "False");
    case BV_INT:
      snprintf(buf, sizeof(buf), "%lld", (long long)v.as.i);
      return bv_xstrdup(buf);
    case BV_FLOAT: {
      snprintf(buf, sizeof(buf), "%.15g", v.as.f);
      /* Match Python: whole floats print with a trailing .0 */
      if (strchr(buf, '.') == NULL && strchr(buf, 'e') == NULL && strchr(buf, 'E') == NULL) {
        size_t n = strlen(buf);
        if (n + 3 < sizeof(buf)) {
          buf[n] = '.';
          buf[n + 1] = '0';
          buf[n + 2] = 0;
        }
      }
      return bv_xstrdup(buf);
    }
    case BV_STR: return bv_xstrdup(v.as.obj->u.str.data);
    case BV_LIST: {
      size_t cap = 64, len = 1;
      char *out = (char *)malloc(cap);
      out[0] = '[';
      out[1] = 0;
      for (size_t i = 0; i < v.as.obj->u.list.len; i++) {
        char *part = bv_format(v.as.obj->u.list.items[i]);
        size_t need = len + strlen(part) + 3;
        if (need > cap) {
          cap = need * 2;
          out = (char *)realloc(out, cap);
        }
        if (i) {
          out[len++] = ',';
          out[len++] = ' ';
          out[len] = 0;
        }
        memcpy(out + len, part, strlen(part) + 1);
        len += strlen(part);
        free(part);
      }
      if (len + 2 > cap) out = (char *)realloc(out, len + 2);
      out[len++] = ']';
      out[len] = 0;
      return out;
    }
    case BV_DICT: return bv_xstrdup("{dict}");
    case BV_CLASS: {
      const char *n = v.as.obj->u.class_.cls ? v.as.obj->u.class_.cls->name : "?";
      snprintf(buf, sizeof(buf), "<class %s>", n);
      return bv_xstrdup(buf);
    }
    case BV_INSTANCE: {
      const char *n = v.as.obj->u.instance.cls ? v.as.obj->u.instance.cls->name : "?";
      snprintf(buf, sizeof(buf), "<%s instance>", n);
      return bv_xstrdup(buf);
    }
    case BV_FUNC:
      snprintf(buf, sizeof(buf), "<fn %s>", v.as.obj->u.func.name ? v.as.obj->u.func.name : "?");
      return bv_xstrdup(buf);
    case BV_MODULE:
      snprintf(buf, sizeof(buf), "<module %s>", v.as.obj->u.module.name ? v.as.obj->u.module.name : "?");
      return bv_xstrdup(buf);
  }
  return bv_xstrdup("?");
}

static bool is_num(BooleValue v) { return v.tag == BV_INT || v.tag == BV_FLOAT || v.tag == BV_BOOL; }

static double as_num(BooleValue v) {
  if (v.tag == BV_FLOAT) return v.as.f;
  if (v.tag == BV_INT) return (double)v.as.i;
  if (v.tag == BV_BOOL) return v.as.b ? 1.0 : 0.0;
  bv_die("expected number");
  return 0;
}

BooleValue bv_add(BooleValue a, BooleValue b) {
  if (a.tag == BV_STR && b.tag == BV_STR) {
    size_t n = a.as.obj->u.str.len + b.as.obj->u.str.len;
    char *buf = (char *)malloc(n + 1);
    memcpy(buf, a.as.obj->u.str.data, a.as.obj->u.str.len);
    memcpy(buf + a.as.obj->u.str.len, b.as.obj->u.str.data, b.as.obj->u.str.len);
    buf[n] = 0;
    BooleValue r = bv_str_n(buf, n);
    free(buf);
    return r;
  }
  if (a.tag == BV_LIST && b.tag == BV_LIST) {
    BooleValue out = bv_list();
    for (size_t i = 0; i < a.as.obj->u.list.len; i++)
      bv_list_push(out, bv_retain(a.as.obj->u.list.items[i]));
    for (size_t i = 0; i < b.as.obj->u.list.len; i++)
      bv_list_push(out, bv_retain(b.as.obj->u.list.items[i]));
    return out;
  }
  if (is_num(a) && is_num(b)) {
    if (a.tag == BV_FLOAT || b.tag == BV_FLOAT) return bv_float(as_num(a) + as_num(b));
    return bv_int(bv_as_int(a) + bv_as_int(b));
  }
  bv_die("bad + operands");
  return bv_none();
}

BooleValue bv_sub(BooleValue a, BooleValue b) {
  if (a.tag == BV_FLOAT || b.tag == BV_FLOAT) return bv_float(as_num(a) - as_num(b));
  return bv_int(bv_as_int(a) - bv_as_int(b));
}

BooleValue bv_mul(BooleValue a, BooleValue b) {
  if (a.tag == BV_STR && b.tag == BV_INT) {
    int64_t n = b.as.i;
    if (n < 0) n = 0;
    size_t len = a.as.obj->u.str.len;
    char *buf = (char *)malloc(len * (size_t)n + 1);
    for (int64_t i = 0; i < n; i++) memcpy(buf + (size_t)i * len, a.as.obj->u.str.data, len);
    buf[len * (size_t)n] = 0;
    BooleValue r = bv_str_n(buf, len * (size_t)n);
    free(buf);
    return r;
  }
  if (a.tag == BV_FLOAT || b.tag == BV_FLOAT) return bv_float(as_num(a) * as_num(b));
  return bv_int(bv_as_int(a) * bv_as_int(b));
}

BooleValue bv_div(BooleValue a, BooleValue b) {
  if (as_num(b) == 0.0) bv_raise("ZeroDivisionError", "division by zero");
  return bv_float(as_num(a) / as_num(b));
}

BooleValue bv_floordiv(BooleValue a, BooleValue b) {
  if (as_num(b) == 0.0) bv_raise("ZeroDivisionError", "division by zero");
  return bv_int((int64_t)floor(as_num(a) / as_num(b)));
}

BooleValue bv_mod(BooleValue a, BooleValue b) {
  if (a.tag == BV_FLOAT || b.tag == BV_FLOAT) {
    if (as_num(b) == 0.0) bv_raise("ZeroDivisionError", "division by zero");
    return bv_float(fmod(as_num(a), as_num(b)));
  }
  if (bv_as_int(b) == 0) bv_raise("ZeroDivisionError", "division by zero");
  return bv_int(bv_as_int(a) % bv_as_int(b));
}

BooleValue bv_pow(BooleValue a, BooleValue b) {
  double r = pow(as_num(a), as_num(b));
  if (a.tag == BV_INT && b.tag == BV_INT && b.as.i >= 0) return bv_int((int64_t)r);
  return bv_float(r);
}

BooleValue bv_neg(BooleValue a) {
  if (a.tag == BV_FLOAT) return bv_float(-a.as.f);
  return bv_int(-bv_as_int(a));
}

bool bv_eq(BooleValue a, BooleValue b) {
  if (a.tag == BV_NONE && b.tag == BV_NONE) return true;
  if (a.tag == BV_BOOL && b.tag == BV_BOOL) return a.as.b == b.as.b;
  if (is_num(a) && is_num(b)) return as_num(a) == as_num(b);
  if (a.tag == BV_STR && b.tag == BV_STR)
    return a.as.obj->u.str.len == b.as.obj->u.str.len &&
           memcmp(a.as.obj->u.str.data, b.as.obj->u.str.data, a.as.obj->u.str.len) == 0;
  return false;
}

bool bv_lt(BooleValue a, BooleValue b) {
  if (is_num(a) && is_num(b)) return as_num(a) < as_num(b);
  if (a.tag == BV_STR && b.tag == BV_STR) return strcmp(a.as.obj->u.str.data, b.as.obj->u.str.data) < 0;
  bv_die("bad < operands");
  return false;
}

bool bv_le(BooleValue a, BooleValue b) { return bv_lt(a, b) || bv_eq(a, b); }
bool bv_gt(BooleValue a, BooleValue b) { return bv_lt(b, a); }
bool bv_ge(BooleValue a, BooleValue b) { return bv_le(b, a); }

void bv_list_push(BooleValue list, BooleValue item) {
  if (list.tag != BV_LIST) bv_die("list push on non-list");
  BooleObj *o = list.as.obj;
  if (o->u.list.len + 1 > o->u.list.cap) {
    size_t ncap = o->u.list.cap ? o->u.list.cap * 2 : 8;
    o->u.list.items = (BooleValue *)realloc(o->u.list.items, ncap * sizeof(BooleValue));
    o->u.list.cap = ncap;
  }
  o->u.list.items[o->u.list.len++] = item;
}

BooleValue bv_list_get(BooleValue list, BooleValue index) {
  if (list.tag != BV_LIST) bv_die("index on non-list");
  int64_t i = bv_as_int(index);
  size_t n = list.as.obj->u.list.len;
  if (i < 0) i += (int64_t)n;
  if (i < 0 || (size_t)i >= n) bv_die("list index out of range");
  return bv_retain(list.as.obj->u.list.items[i]);
}

void bv_list_set(BooleValue list, BooleValue index, BooleValue item) {
  if (list.tag != BV_LIST) bv_die("index assign on non-list");
  int64_t i = bv_as_int(index);
  size_t n = list.as.obj->u.list.len;
  if (i < 0) i += (int64_t)n;
  if (i < 0 || (size_t)i >= n) bv_die("list index out of range");
  bv_release(list.as.obj->u.list.items[i]);
  list.as.obj->u.list.items[i] = item;
}

void bv_dict_set(BooleValue dict, BooleValue key, BooleValue value) {
  if (dict.tag != BV_DICT) bv_die("dict set on non-dict");
  BooleObj *o = dict.as.obj;
  for (size_t i = 0; i < o->u.dict.len; i++) {
    if (bv_eq(o->u.dict.keys[i], key)) {
      bv_release(o->u.dict.vals[i]);
      o->u.dict.vals[i] = value;
      bv_release(key);
      return;
    }
  }
  if (o->u.dict.len + 1 > o->u.dict.cap) {
    size_t ncap = o->u.dict.cap ? o->u.dict.cap * 2 : 8;
    o->u.dict.keys = (BooleValue *)realloc(o->u.dict.keys, ncap * sizeof(BooleValue));
    o->u.dict.vals = (BooleValue *)realloc(o->u.dict.vals, ncap * sizeof(BooleValue));
    o->u.dict.cap = ncap;
  }
  o->u.dict.keys[o->u.dict.len] = key;
  o->u.dict.vals[o->u.dict.len] = value;
  o->u.dict.len++;
}

BooleValue bv_dict_get(BooleValue dict, BooleValue key) {
  if (dict.tag != BV_DICT) bv_die("dict get on non-dict");
  BooleObj *o = dict.as.obj;
  for (size_t i = 0; i < o->u.dict.len; i++) {
    if (bv_eq(o->u.dict.keys[i], key)) return bv_retain(o->u.dict.vals[i]);
  }
  bv_die("KeyError");
  return bv_none();
}

BooleValue bv_index_get(BooleValue obj, BooleValue index) {
  if (obj.tag == BV_LIST) return bv_list_get(obj, index);
  if (obj.tag == BV_DICT) return bv_dict_get(obj, index);
  if (obj.tag == BV_STR) {
    int64_t i = bv_as_int(index);
    size_t n = obj.as.obj->u.str.len;
    if (i < 0) i += (int64_t)n;
    if (i < 0 || (size_t)i >= n) bv_die("string index out of range");
    return bv_str_n(obj.as.obj->u.str.data + i, 1);
  }
  bv_die("index on bad type");
  return bv_none();
}

void bv_index_set(BooleValue obj, BooleValue index, BooleValue value) {
  if (obj.tag == BV_LIST) {
    bv_list_set(obj, index, value);
    return;
  }
  if (obj.tag == BV_DICT) {
    bv_dict_set(obj, bv_retain(index), value);
    return;
  }
  bv_release(value);
  bv_die("index assign on bad type");
}

BooleValue bv_list_slice(BooleValue list, BooleValue start, BooleValue stop) {
  if (list.tag != BV_LIST) bv_die("slice on non-list");
  int64_t n = (int64_t)list.as.obj->u.list.len;
  int64_t a = start.tag == BV_NONE ? 0 : bv_as_int(start);
  int64_t b = stop.tag == BV_NONE ? n : bv_as_int(stop);
  if (a < 0) a += n;
  if (b < 0) b += n;
  if (a < 0) a = 0;
  if (b > n) b = n;
  if (a > b) a = b;
  BooleValue out = bv_list();
  for (int64_t i = a; i < b; i++) bv_list_push(out, bv_retain(list.as.obj->u.list.items[i]));
  return out;
}

BooleValue bv_slice(BooleValue obj, BooleValue start, BooleValue stop) {
  if (obj.tag == BV_LIST) return bv_list_slice(obj, start, stop);
  if (obj.tag == BV_STR) {
    int64_t n = (int64_t)obj.as.obj->u.str.len;
    int64_t a = start.tag == BV_NONE ? 0 : bv_as_int(start);
    int64_t b = stop.tag == BV_NONE ? n : bv_as_int(stop);
    if (a < 0) a += n;
    if (b < 0) b += n;
    if (a < 0) a = 0;
    if (b > n) b = n;
    if (a > b) a = b;
    return bv_str_n(obj.as.obj->u.str.data + a, (size_t)(b - a));
  }
  bv_die("slice on bad type");
  return bv_none();
}

BooleValue bv_call_print(int argc, BooleValue *argv) {
  for (int i = 0; i < argc; i++) {
    if (i) fputc(' ', stdout);
    char *s = bv_format(argv[i]);
    fputs(s, stdout);
    free(s);
  }
  fputc('\n', stdout);
  return bv_none();
}

BooleValue bv_call_len(BooleValue v) {
  if (v.tag == BV_STR) return bv_int((int64_t)v.as.obj->u.str.len);
  if (v.tag == BV_LIST) return bv_int((int64_t)v.as.obj->u.list.len);
  if (v.tag == BV_DICT) return bv_int((int64_t)v.as.obj->u.dict.len);
  bv_die("len() bad type");
  return bv_none();
}

BooleValue bv_call_range(int argc, BooleValue *argv) {
  int64_t start = 0, stop = 0, step = 1;
  if (argc == 1) {
    stop = bv_as_int(argv[0]);
  } else if (argc == 2) {
    start = bv_as_int(argv[0]);
    stop = bv_as_int(argv[1]);
  } else if (argc == 3) {
    start = bv_as_int(argv[0]);
    stop = bv_as_int(argv[1]);
    step = bv_as_int(argv[2]);
    if (step == 0) bv_die("range() step is zero");
  } else {
    bv_die("range() bad argc");
  }
  BooleValue out = bv_list();
  if (step > 0) {
    for (int64_t i = start; i < stop; i += step) bv_list_push(out, bv_int(i));
  } else {
    for (int64_t i = start; i > stop; i += step) bv_list_push(out, bv_int(i));
  }
  return out;
}

BooleValue bv_call_str(BooleValue v) {
  char *s = bv_format(v);
  BooleValue r = bv_str(s);
  free(s);
  return r;
}

BooleValue bv_call_int(BooleValue v) {
  if (v.tag == BV_INT) return bv_int(v.as.i);
  if (v.tag == BV_BOOL) return bv_int(v.as.b ? 1 : 0);
  if (v.tag == BV_FLOAT) return bv_int((int64_t)v.as.f);
  if (v.tag == BV_STR) return bv_int(atoll(v.as.obj->u.str.data));
  bv_die("int() bad type");
  return bv_none();
}

BooleValue bv_call_float(BooleValue v) {
  if (v.tag == BV_FLOAT) return bv_float(v.as.f);
  if (v.tag == BV_INT) return bv_float((double)v.as.i);
  if (v.tag == BV_STR) return bv_float(atof(v.as.obj->u.str.data));
  bv_die("float() bad type");
  return bv_none();
}

BooleValue bv_call_bool(BooleValue v) { return bv_bool(bv_truthy(v)); }

BooleValue bv_call_sorted(BooleValue v) {
  if (v.tag != BV_LIST) bv_die("sorted() expects list");
  BooleValue out = bv_list();
  for (size_t i = 0; i < v.as.obj->u.list.len; i++)
    bv_list_push(out, bv_retain(v.as.obj->u.list.items[i]));
  size_t n = out.as.obj->u.list.len;
  for (size_t i = 0; i < n; i++) {
    for (size_t j = i + 1; j < n; j++) {
      if (bv_lt(out.as.obj->u.list.items[j], out.as.obj->u.list.items[i])) {
        BooleValue tmp = out.as.obj->u.list.items[i];
        out.as.obj->u.list.items[i] = out.as.obj->u.list.items[j];
        out.as.obj->u.list.items[j] = tmp;
      }
    }
  }
  return out;
}

BooleValue bv_call_max(int argc, BooleValue *argv) {
  BooleValue best;
  size_t n;
  BooleValue *items;
  if (argc == 1 && argv[0].tag == BV_LIST) {
    items = argv[0].as.obj->u.list.items;
    n = argv[0].as.obj->u.list.len;
    if (n == 0) bv_die("max() empty");
    best = items[0];
    for (size_t i = 1; i < n; i++)
      if (bv_gt(items[i], best)) best = items[i];
    return bv_retain(best);
  }
  if (argc < 1) bv_die("max() needs args");
  best = argv[0];
  for (int i = 1; i < argc; i++)
    if (bv_gt(argv[i], best)) best = argv[i];
  return bv_retain(best);
}

BooleValue bv_call_min(int argc, BooleValue *argv) {
  BooleValue best;
  if (argc == 1 && argv[0].tag == BV_LIST) {
    size_t n = argv[0].as.obj->u.list.len;
    if (n == 0) bv_die("min() empty");
    best = argv[0].as.obj->u.list.items[0];
    for (size_t i = 1; i < n; i++)
      if (bv_lt(argv[0].as.obj->u.list.items[i], best)) best = argv[0].as.obj->u.list.items[i];
    return bv_retain(best);
  }
  if (argc < 1) bv_die("min() needs args");
  best = argv[0];
  for (int i = 1; i < argc; i++)
    if (bv_lt(argv[i], best)) best = argv[i];
  return bv_retain(best);
}

BooleValue bv_call_sum(BooleValue v) {
  if (v.tag != BV_LIST) bv_die("sum() expects list");
  int64_t total = 0;
  bool any_float = false;
  double ftotal = 0;
  for (size_t i = 0; i < v.as.obj->u.list.len; i++) {
    BooleValue x = v.as.obj->u.list.items[i];
    if (x.tag == BV_FLOAT) {
      any_float = true;
      ftotal += as_num(x);
    } else {
      total += bv_as_int(x);
      ftotal += as_num(x);
    }
  }
  return any_float ? bv_float(ftotal) : bv_int(total);
}

BooleValue bv_call_abs(BooleValue v) {
  if (v.tag == BV_FLOAT) return bv_float(fabs(v.as.f));
  int64_t i = bv_as_int(v);
  return bv_int(i < 0 ? -i : i);
}

BooleValue bv_call_type(BooleValue v) {
  switch (v.tag) {
    case BV_NONE: return bv_str("None");
    case BV_BOOL: return bv_str("bool");
    case BV_INT: return bv_str("int");
    case BV_FLOAT: return bv_str("float");
    case BV_STR: return bv_str("str");
    case BV_LIST: return bv_str("list");
    case BV_DICT: return bv_str("dict");
    case BV_CLASS: return bv_str("class");
    case BV_INSTANCE: return bv_str("instance");
    case BV_FUNC: return bv_str("function");
    case BV_MODULE: return bv_str("module");
  }
  return bv_str("?");
}

BooleValue bv_getattr(BooleValue obj, const char *name) {
  if (obj.tag == BV_INSTANCE) {
    BooleValue key = bv_str(name);
    /* dict get dies on missing — scan manually */
    BooleObj *d = obj.as.obj->u.instance.fields.as.obj;
    for (size_t i = 0; i < d->u.dict.len; i++) {
      if (d->u.dict.keys[i].tag == BV_STR &&
          strcmp(d->u.dict.keys[i].as.obj->u.str.data, name) == 0) {
        bv_release(key);
        return bv_retain(d->u.dict.vals[i]);
      }
    }
    bv_release(key);
    char buf[128];
    snprintf(buf, sizeof(buf), "attribute '%s' not found", name);
    bv_die(buf);
  }
  if (obj.tag == BV_MODULE) {
    BooleObj *d = obj.as.obj->u.module.attrs.as.obj;
    for (size_t i = 0; i < d->u.dict.len; i++) {
      if (d->u.dict.keys[i].tag == BV_STR &&
          strcmp(d->u.dict.keys[i].as.obj->u.str.data, name) == 0) {
        return bv_retain(d->u.dict.vals[i]);
      }
    }
    char buf[128];
    snprintf(buf, sizeof(buf), "module has no attribute '%s'", name);
    bv_die(buf);
  }
  bv_die("getattr on unsupported type");
  return bv_none();
}

void bv_setattr(BooleValue obj, const char *name, BooleValue value) {
  if (obj.tag == BV_INSTANCE) {
    BooleValue key = bv_str(name);
    bv_dict_set(obj.as.obj->u.instance.fields, key, value);
    return;
  }
  if (obj.tag == BV_MODULE) {
    BooleValue key = bv_str(name);
    bv_dict_set(obj.as.obj->u.module.attrs, key, value);
    return;
  }
  bv_release(value);
  bv_die("setattr on unsupported type");
}
