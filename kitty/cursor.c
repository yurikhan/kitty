/*
 * cursor.c
 * Copyright (C) 2016 Kovid Goyal <kovid at kovidgoyal.net>
 *
 * Distributed under terms of the GPL3 license.
 */

#include "data-types.h"

#include <structmember.h>

static PyObject *
new(PyTypeObject *type, PyObject UNUSED *args, PyObject UNUSED *kwds) {
    Cursor *self;

    self = (Cursor *)type->tp_alloc(type, 0);
    return (PyObject*) self;
}

static void
dealloc(Cursor* self) {
    Py_TYPE(self)->tp_free((PyObject*)self);
}

#define EQ(x) (a->x == b->x)
static int __eq__(Cursor *a, Cursor *b) {
    return EQ(bold) && EQ(italic) && EQ(strikethrough) && EQ(dim) && EQ(reverse) && EQ(decoration) && EQ(fg) && EQ(bg) && EQ(decoration_fg) && EQ(x) && EQ(y) && EQ(shape) && EQ(blink);
}

static const char* cursor_names[NUM_OF_CURSOR_SHAPES] = { "NO_SHAPE", "BLOCK", "BEAM", "UNDERLINE" };

#define BOOL(x) ((x) ? Py_True : Py_False)
static PyObject *
repr(Cursor *self) {
    return PyUnicode_FromFormat(
        "Cursor(x=%u, y=%u, shape=%s, blink=%R, fg=#%08x, bg=#%08x, bold=%R, italic=%R, reverse=%R, strikethrough=%R, dim=%R, decoration=%d, decoration_fg=#%08x)",
        self->x, self->y, (self->shape < NUM_OF_CURSOR_SHAPES ? cursor_names[self->shape] : "INVALID"),
        BOOL(self->blink), self->fg, self->bg, BOOL(self->bold), BOOL(self->italic), BOOL(self->reverse), BOOL(self->strikethrough), BOOL(self->dim), self->decoration, self->decoration_fg
    );
}

void
cursor_reset_display_attrs(Cursor *self) {
    self->bg = 0; self->fg = 0; self->decoration_fg = 0;
    self->decoration = 0; self->bold = false; self->italic = false; self->reverse = false; self->strikethrough = false; self->dim = false;
}


static inline void
parse_color(unsigned int *params, unsigned int *i, unsigned int count, uint32_t *result) {
    unsigned int attr;
    uint8_t r, g, b;
    if (*i < count) {
        attr = params[(*i)++];
        switch(attr) {
            case 5:
                if (*i < count) *result = (params[(*i)++] & 0xFF) << 8 | 1;
                break;
            case 2: \
                if (*i < count - 2) {
                    /* Ignore the first parameter in a four parameter RGB */
                    /* sequence (unused color space id), see https://github.com/kovidgoyal/kitty/issues/227 */
                    if (*i < count - 3) (*i)++;
                    r = params[(*i)++] & 0xFF;
                    g = params[(*i)++] & 0xFF;
                    b = params[(*i)++] & 0xFF;
                    *result = r << 24 | g << 16 | b << 8 | 2;
                }
                break;
        }
    }
}


void
cursor_from_sgr(Cursor *self, unsigned int *params, unsigned int count) {
#define SET_COLOR(which) { parse_color(params, &i, count, &self->which); } break;
START_ALLOW_CASE_RANGE
    unsigned int i = 0, attr;
    if (!count) { params[0] = 0; count = 1; }
    while (i < count) {
        attr = params[i++];
        switch(attr) {
            case 0:
                cursor_reset_display_attrs(self);  break;
            case 1:
                self->bold = true;  break;
            case 2:
                self->dim = true; break;
            case 3:
                self->italic = true;  break;
            case 4:
                if (i < count) { self->decoration = MIN(3u, params[i]); i++; }
                else self->decoration = 1;
                break;
            case 7:
                self->reverse = true;  break;
            case 9:
                self->strikethrough = true;  break;
            case 21:
                self->decoration = 2; break;
            case 22:
                self->bold = false;  self->dim = false; break;
            case 23:
                self->italic = false;  break;
            case 24:
                self->decoration = 0;  break;
            case 27:
                self->reverse = false;  break;
            case 29:
                self->strikethrough = false;  break;
            case 30 ... 37:
                self->fg = ((attr - 30) << 8) | 1;  break;
            case 38:
                SET_COLOR(fg);
            case 39:
                self->fg = 0;  break;
            case 40 ... 47:
                self->bg = ((attr - 40) << 8) | 1;  break;
            case 48:
                SET_COLOR(bg);
            case 49:
                self->bg = 0;  break;
            case 90 ... 97:
                self->fg = ((attr - 90 + 8) << 8) | 1;  break;
            case 100 ... 107:
                self->bg = ((attr - 100 + 8) << 8) | 1;  break;
            case DECORATION_FG_CODE:
                SET_COLOR(decoration_fg);
            case DECORATION_FG_CODE + 1:
                self->decoration_fg = 0; break;
        }
    }
#undef SET_COLOR
END_ALLOW_CASE_RANGE
}

void
apply_sgr_to_cells(GPUCell *first_cell, unsigned int cell_count, unsigned int *params, unsigned int count) {
#define RANGE for(unsigned c = 0; c < cell_count; c++, cell++)
#define SET(shift) RANGE { cell->attrs |= (1 << shift); } break;
#define RESET(shift) RANGE { cell->attrs &= ~(1 << shift); } break;
#define RESET2(shift1, shift2) RANGE { cell->attrs &= ~((1 << shift1) | (1 << shift2)); } break;
#define SETM(val, mask, shift) { RANGE { cell->attrs &= ~(mask << shift); cell->attrs |= ((val) << shift); } break; }
#define SET_COLOR(which) { color_type color = 0; parse_color(params, &i, count, &color); if (color) { RANGE { cell->which = color; }} } break;
#define SIMPLE(which, val) RANGE { cell->which = (val); } break;

    unsigned int i = 0, attr;
    if (!count) { params[0] = 0; count = 1; }
    while (i < count) {
        GPUCell *cell = first_cell;
        attr = params[i++];
        switch(attr) {
            case 0:
                RANGE { cell->attrs &= WIDTH_MASK; cell->fg = 0; cell->bg = 0; cell->decoration_fg = 0; }
                break;
            case 1:
                SET(BOLD_SHIFT);
            case 2:
                SET(DIM_SHIFT);
            case 3:
                SET(ITALIC_SHIFT);
            case 4:
                if (i < count) { uint8_t val = MIN(3u, params[i]); i++; SETM(val, DECORATION_MASK, DECORATION_SHIFT); }
                else { SETM(1, DECORATION_MASK, DECORATION_SHIFT); }
            case 7:
                SET(REVERSE_SHIFT);
            case 9:
                SET(STRIKE_SHIFT);
            case 21:
                SETM(2, DECORATION_MASK, DECORATION_SHIFT);
            case 22:
                RESET2(DIM_SHIFT, BOLD_SHIFT);
            case 23:
                RESET(ITALIC_SHIFT);
            case 24:
                SETM(0, DECORATION_MASK, DECORATION_SHIFT);
            case 27:
                RESET(REVERSE_SHIFT);
            case 29:
                RESET(STRIKE_SHIFT);
START_ALLOW_CASE_RANGE
            case 30 ... 37:
                SIMPLE(fg, ((attr - 30) << 8) | 1);
            case 38:
                SET_COLOR(fg);
            case 39:
                SIMPLE(fg, 0);
            case 40 ... 47:
                SIMPLE(bg, ((attr - 40) << 8) | 1);
            case 48:
                SET_COLOR(bg);
            case 49:
                SIMPLE(bg, 0);
            case 90 ... 97:
                SIMPLE(fg, ((attr - 90 + 8) << 8) | 1);
            case 100 ... 107:
                SIMPLE(bg, ((attr - 100 + 8) << 8) | 1);
END_ALLOW_CASE_RANGE
            case DECORATION_FG_CODE:
                SET_COLOR(decoration_fg);
            case DECORATION_FG_CODE + 1:
                SIMPLE(decoration_fg, 0);
        }
    }
#undef RESET
#undef RESET2
#undef SET_COLOR
#undef SET
#undef SETM
#undef RANGE
}

const char*
cursor_as_sgr(const Cursor *self) {
    GPUCell blank_cell = { 0 }, cursor_cell = {
        .attrs = CURSOR_TO_ATTRS(self, 1),
        .fg = self->fg & COL_MASK,
        .bg = self->bg & COL_MASK,
        .decoration_fg = self->decoration_fg & COL_MASK,
    };
    return cell_as_sgr(&cursor_cell, &blank_cell);
}

static PyObject *
reset_display_attrs(Cursor *self, PyObject *a UNUSED) {
#define reset_display_attrs_doc "Reset all display attributes to unset"
    cursor_reset_display_attrs(self);
    Py_RETURN_NONE;
}

void cursor_reset(Cursor *self) {
    cursor_reset_display_attrs(self);
    self->x = 0; self->y = 0;
    self->shape = NO_CURSOR_SHAPE; self->blink = false;
}

void cursor_copy_to(Cursor *src, Cursor *dest) {
#define CCY(x) dest->x = src->x;
    CCY(x); CCY(y); CCY(shape); CCY(blink);
    CCY(bold); CCY(italic); CCY(strikethrough); CCY(dim); CCY(reverse); CCY(decoration); CCY(fg); CCY(bg); CCY(decoration_fg);
}

static PyObject*
copy(Cursor *self, PyObject*);
#define copy_doc "Create a clone of this cursor"

// Boilerplate {{{

BOOL_GETSET(Cursor, bold)
BOOL_GETSET(Cursor, italic)
BOOL_GETSET(Cursor, reverse)
BOOL_GETSET(Cursor, strikethrough)
BOOL_GETSET(Cursor, dim)
BOOL_GETSET(Cursor, blink)

static PyMemberDef members[] = {
    {"x", T_UINT, offsetof(Cursor, x), 0, "x"},
    {"y", T_UINT, offsetof(Cursor, y), 0, "y"},
    {"shape", T_INT, offsetof(Cursor, shape), 0, "shape"},
    {"decoration", T_UBYTE, offsetof(Cursor, decoration), 0, "decoration"},
    {"fg", T_UINT, offsetof(Cursor, fg), 0, "fg"},
    {"bg", T_UINT, offsetof(Cursor, bg), 0, "bg"},
    {"decoration_fg", T_UINT, offsetof(Cursor, decoration_fg), 0, "decoration_fg"},
    {NULL}  /* Sentinel */
};

static PyGetSetDef getseters[] = {
    GETSET(bold)
    GETSET(italic)
    GETSET(reverse)
    GETSET(strikethrough)
    GETSET(dim)
    GETSET(blink)
    {NULL}  /* Sentinel */
};

static PyMethodDef methods[] = {
    METHOD(copy, METH_NOARGS)
    METHOD(reset_display_attrs, METH_NOARGS)
    {NULL}  /* Sentinel */
};


static PyObject *
richcmp(PyObject *obj1, PyObject *obj2, int op);

PyTypeObject Cursor_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "fast_data_types.Cursor",
    .tp_basicsize = sizeof(Cursor),
    .tp_dealloc = (destructor)dealloc,
    .tp_repr = (reprfunc)repr,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "Cursors",
    .tp_richcompare = richcmp,
    .tp_methods = methods,
    .tp_members = members,
    .tp_getset = getseters,
    .tp_new = new,
};

RICHCMP(Cursor)

// }}}

Cursor*
cursor_copy(Cursor *self) {
    Cursor* ans;
    ans = alloc_cursor();
    if (ans == NULL) { PyErr_NoMemory(); return NULL; }
    cursor_copy_to(self, ans);
    return ans;
}

static PyObject*
copy(Cursor *self, PyObject *a UNUSED) {
    return (PyObject*)cursor_copy(self);
}

Cursor *alloc_cursor() {
    return (Cursor*)new(&Cursor_Type, NULL, NULL);
}

INIT_TYPE(Cursor)
