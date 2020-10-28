#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import json
import os
import re
import sys
from contextlib import contextmanager, suppress
from functools import partial
from typing import (
    Any, Callable, Dict, Generator, Iterable, List, NamedTuple, Optional,
    Sequence, Set, Tuple, Type, Union
)

from . import fast_data_types as defines
from .conf.definition import as_conf_file, config_lines
from .conf.utils import (
    BadLine, init_config, key_func, load_config as _load_config, merge_dicts,
    parse_config_base, python_string, to_bool, to_cmdline
)
from .config_data import all_options, parse_mods, type_convert
from .constants import cache_dir, defconf, is_macos
from .key_names import get_key_name_lookup, key_name_aliases
from .options_stub import Options as OptionsStub
from .typing import TypedDict
from .utils import expandvars, log_error

KeySpec = Tuple[int, bool, int]
KeyMap = Dict[KeySpec, 'KeyAction']
KeySequence = Tuple[KeySpec, ...]
SubSequenceMap = Dict[KeySequence, 'KeyAction']
SequenceMap = Dict[KeySpec, SubSequenceMap]


class InvalidMods(ValueError):
    pass


def parse_shortcut(sc: str) -> Tuple[int, bool, Optional[int]]:
    parts = sc.split('+')
    mods = 0
    if len(parts) > 1:
        mods = parse_mods(parts[:-1], sc) or 0
        if not mods:
            raise InvalidMods('Invalid shortcut')
    q = parts[-1].upper()
    key: Optional[int] = getattr(defines, 'GLFW_KEY_' + key_name_aliases.get(q, q), None)
    is_native = False
    if key is None:
        q = parts[-1]
        if q.startswith('0x'):
            with suppress(Exception):
                key = int(q, 16)
        else:
            key = get_key_name_lookup()(q, False)
        is_native = key is not None
    return mods, is_native, key


class KeyAction(NamedTuple):
    func: str
    args: Sequence[str]


func_with_args, args_funcs = key_func()
FuncArgsType = Tuple[str, Sequence[Any]]


@func_with_args(
    'pass_selection_to_program', 'new_window', 'new_tab', 'new_os_window',
    'new_window_with_cwd', 'new_tab_with_cwd', 'new_os_window_with_cwd',
    'launch'
    )
def shlex_parse(func: str, rest: str) -> FuncArgsType:
    return func, to_cmdline(rest)


@func_with_args('combine')
def combine_parse(func: str, rest: str) -> FuncArgsType:
    sep, rest = rest.split(maxsplit=1)
    parts = re.split(r'\s*' + re.escape(sep) + r'\s*', rest)
    args = tuple(map(parse_key_action, filter(None, parts)))
    return func, args


@func_with_args('send_text')
def send_text_parse(func: str, rest: str) -> FuncArgsType:
    args = rest.split(maxsplit=1)
    mode = ''
    data = b''
    if len(args) > 1:
        mode = args[0]
        try:
            data = parse_send_text_bytes(args[1])
        except Exception:
            log_error('Ignoring invalid send_text string: ' + args[1])
    return func, [mode, data]


@func_with_args('run_kitten', 'run_simple_kitten', 'kitten')
def kitten_parse(func: str, rest: str) -> FuncArgsType:
    if func == 'kitten':
        args = rest.split(maxsplit=1)
    else:
        args = rest.split(maxsplit=2)[1:]
        func = 'kitten'
    return func, args


@func_with_args('goto_tab')
def goto_tab_parse(func: str, rest: str) -> FuncArgsType:
    args = (max(0, int(rest)), )
    return func, args


@func_with_args('detach_window')
def detach_window_parse(func: str, rest: str) -> FuncArgsType:
    if rest not in ('new', 'new-tab', 'ask'):
        log_error('Ignoring invalid detach_window argument: {}'.format(rest))
        rest = 'new'
    return func, (rest,)


@func_with_args('detach_tab')
def detach_tab_parse(func: str, rest: str) -> FuncArgsType:
    if rest not in ('new', 'ask'):
        log_error('Ignoring invalid detach_tab argument: {}'.format(rest))
        rest = 'new'
    return func, (rest,)


@func_with_args('set_background_opacity', 'goto_layout', 'kitty_shell')
def simple_parse(func: str, rest: str) -> FuncArgsType:
    return func, [rest]


@func_with_args('set_font_size')
def float_parse(func: str, rest: str) -> FuncArgsType:
    return func, (float(rest),)


@func_with_args('signal_child')
def signal_child_parse(func: str, rest: str) -> FuncArgsType:
    import signal
    signals = []
    for q in rest.split():
        try:
            signum = getattr(signal, q.upper())
        except AttributeError:
            log_error(f'Unknown signal: {rest} ignoring')
        else:
            signals.append(signum)
    return func, tuple(signals)


@func_with_args('change_font_size')
def parse_change_font_size(func: str, rest: str) -> Tuple[str, Tuple[bool, Optional[str], float]]:
    vals = rest.strip().split(maxsplit=1)
    if len(vals) != 2:
        log_error('Invalid change_font_size specification: {}, treating it as default'.format(rest))
        return func, (True, None, 0)
    c_all = vals[0].lower() == 'all'
    sign: Optional[str] = None
    amt = vals[1]
    if amt[0] in '+-':
        sign = amt[0]
        amt = amt[1:]
    return func, (c_all, sign, float(amt.strip()))


@func_with_args('clear_terminal')
def clear_terminal(func: str, rest: str) -> FuncArgsType:
    vals = rest.strip().split(maxsplit=1)
    if len(vals) != 2:
        log_error('clear_terminal needs two arguments, using defaults')
        args: List[Union[str, bool]] = ['reset', 'active']
    else:
        args = [vals[0].lower(), vals[1].lower() == 'active']
    return func, args


@func_with_args('copy_to_buffer')
def copy_to_buffer(func: str, rest: str) -> FuncArgsType:
    return func, [rest]


@func_with_args('paste_from_buffer')
def paste_from_buffer(func: str, rest: str) -> FuncArgsType:
    return func, [rest]


@func_with_args('neighboring_window')
def neighboring_window(func: str, rest: str) -> FuncArgsType:
    rest = rest.lower()
    rest = {'up': 'top', 'down': 'bottom'}.get(rest, rest)
    if rest not in ('left', 'right', 'top', 'bottom'):
        log_error('Invalid neighbor specification: {}'.format(rest))
        rest = 'right'
    return func, [rest]


@func_with_args('resize_window')
def resize_window(func: str, rest: str) -> FuncArgsType:
    vals = rest.strip().split(maxsplit=1)
    if len(vals) > 2:
        log_error('resize_window needs one or two arguments, using defaults')
        args = ['wider', 1]
    else:
        quality = vals[0].lower()
        if quality not in ('taller', 'shorter', 'wider', 'narrower'):
            log_error('Invalid quality specification: {}'.format(quality))
            quality = 'wider'
        increment = 1
        if len(vals) == 2:
            try:
                increment = int(vals[1])
            except Exception:
                log_error('Invalid increment specification: {}'.format(vals[1]))
        args = [quality, increment]
    return func, args


@func_with_args('move_window')
def move_window(func: str, rest: str) -> FuncArgsType:
    rest = rest.lower()
    rest = {'up': 'top', 'down': 'bottom'}.get(rest, rest)
    prest: Union[int, str] = rest
    try:
        prest = int(prest)
    except Exception:
        if prest not in ('left', 'right', 'top', 'bottom'):
            log_error('Invalid move_window specification: {}'.format(rest))
            prest = 0
    return func, [prest]


@func_with_args('pipe')
def pipe(func: str, rest: str) -> FuncArgsType:
    import shlex
    r = shlex.split(rest)
    if len(r) < 3:
        log_error('Too few arguments to pipe function')
        r = ['none', 'none', 'true']
    return func, r


@func_with_args('set_colors')
def set_colors(func: str, rest: str) -> FuncArgsType:
    import shlex
    r = shlex.split(rest)
    if len(r) < 1:
        log_error('Too few arguments to set_colors function')
    return func, r


@func_with_args('remote_control')
def remote_control(func: str, rest: str) -> FuncArgsType:
    import shlex
    r = shlex.split(rest)
    if len(r) < 1:
        log_error('Too few arguments to remote_control function')
    return func, r


@func_with_args('nth_window')
def nth_window(func: str, rest: str) -> FuncArgsType:
    try:
        num = int(rest)
    except Exception:
        log_error('Invalid nth_window number: {}'.format(rest))
        num = 1
    return func, [num]


@func_with_args('disable_ligatures_in')
def disable_ligatures_in(func: str, rest: str) -> FuncArgsType:
    parts = rest.split(maxsplit=1)
    if len(parts) == 1:
        where, strategy = 'active', parts[0]
    else:
        where, strategy = parts
    if where not in ('active', 'all', 'tab'):
        raise ValueError('{} is not a valid set of windows to disable ligatures in'.format(where))
    if strategy not in ('never', 'always', 'cursor'):
        raise ValueError('{} is not a valid disable ligatures strategy'.format(strategy))
    return func, [where, strategy]


@func_with_args('layout_action')
def layout_action(func: str, rest: str) -> FuncArgsType:
    parts = rest.split(maxsplit=1)
    if not parts:
        raise ValueError('layout_action must have at least one argument')
    return func, [parts[0], tuple(parts[1:])]


def parse_marker_spec(ftype: str, parts: Sequence[str]) -> Tuple[str, Union[str, Tuple[Tuple[int, str], ...]], int]:
    flags = re.UNICODE
    if ftype in ('text', 'itext', 'regex', 'iregex'):
        if ftype.startswith('i'):
            flags |= re.IGNORECASE
        if not parts or len(parts) % 2 != 0:
            raise ValueError('No color specified in marker: {}'.format(' '.join(parts)))
        ans = []
        for i in range(0, len(parts), 2):
            try:
                color = max(1, min(int(parts[i]), 3))
            except Exception:
                raise ValueError('color {} in marker specification is not an integer'.format(parts[i]))
            sspec = parts[i + 1]
            if 'regex' not in ftype:
                sspec = re.escape(sspec)
            ans.append((color, sspec))
        ftype = 'regex'
        spec: Union[str, Tuple[Tuple[int, str], ...]] = tuple(ans)
    elif ftype == 'function':
        spec = ' '.join(parts)
    else:
        raise ValueError('Unknown marker type: {}'.format(ftype))
    return ftype, spec, flags


@func_with_args('toggle_marker')
def toggle_marker(func: str, rest: str) -> FuncArgsType:
    parts = rest.split(maxsplit=1)
    if len(parts) != 2:
        raise ValueError('{} is not a valid marker specification'.format(rest))
    ftype, spec = parts
    parts = spec.split()
    return func, list(parse_marker_spec(ftype, parts))


@func_with_args('scroll_to_mark')
def scroll_to_mark(func: str, rest: str) -> FuncArgsType:
    parts = rest.split()
    if not parts or not rest:
        return func, [True, 0]
    if len(parts) == 1:
        q = parts[0].lower()
        if q in ('prev', 'previous', 'next'):
            return func, [q != 'next', 0]
        try:
            return func, [True, max(0, min(int(q), 3))]
        except Exception:
            raise ValueError('{} is not a valid scroll_to_mark destination'.format(rest))
    return func, [parts[0] != 'next', max(0, min(int(parts[1]), 3))]


def parse_key_action(action: str) -> Optional[KeyAction]:
    parts = action.strip().split(maxsplit=1)
    func = parts[0]
    if len(parts) == 1:
        return KeyAction(func, ())
    rest = parts[1]
    parser = args_funcs.get(func)
    if parser is not None:
        try:
            func, args = parser(func, rest)
        except Exception as err:
            log_error('Ignoring invalid key action: {} with err: {}'.format(action, err))
        else:
            return KeyAction(func, args)
    return None


all_key_actions: Set[str] = set()
sequence_sep = '>'


class KeyDefinition:

    def __init__(self, is_sequence: bool, action: KeyAction, mods: int, is_native: bool, key: int, rest: Tuple[KeySpec, ...] = ()):
        self.is_sequence = is_sequence
        self.action = action
        self.trigger = mods, is_native, key
        self.rest = rest

    def resolve(self, kitty_mod: int) -> None:
        self.trigger = defines.resolve_key_mods(kitty_mod, self.trigger[0]), self.trigger[1], self.trigger[2]
        self.rest = tuple((defines.resolve_key_mods(kitty_mod, mods), is_native, key) for mods, is_native, key in self.rest)

    def resolve_kitten_aliases(self, aliases: Dict[str, Sequence[str]]) -> None:
        if not self.action.args:
            return
        kitten = self.action.args[0]
        rest = self.action.args[1] if len(self.action.args) > 1 else ''
        changed = False
        for key, expanded in aliases.items():
            if key == kitten:
                changed = True
                kitten = expanded[0]
                if len(expanded) > 1:
                    rest = expanded[1] + ' ' + rest
        if changed:
            self.action = self.action._replace(args=[kitten, rest.rstrip()])


def parse_key(val: str, key_definitions: List[KeyDefinition]) -> None:
    parts = val.split(maxsplit=1)
    if len(parts) != 2:
        return
    sc, action = parts
    sc, action = sc.strip().strip(sequence_sep), action.strip()
    if not sc or not action:
        return
    is_sequence = sequence_sep in sc
    if is_sequence:
        trigger: Optional[Tuple[int, bool, int]] = None
        restl: List[Tuple[int, bool, int]] = []
        for part in sc.split(sequence_sep):
            try:
                mods, is_native, key = parse_shortcut(part)
            except InvalidMods:
                return
            if key is None:
                if mods is not None:
                    log_error('Shortcut: {} has unknown key, ignoring'.format(sc))
                return
            if trigger is None:
                trigger = mods, is_native, key
            else:
                restl.append((mods, is_native, key))
        rest = tuple(restl)
    else:
        try:
            mods, is_native, key = parse_shortcut(sc)
        except InvalidMods:
            return
        if key is None:
            if mods is not None:
                log_error('Shortcut: {} has unknown key, ignoring'.format(sc))
            return
    try:
        paction = parse_key_action(action)
    except Exception:
        log_error('Invalid shortcut action: {}. Ignoring.'.format(
            action))
    else:
        if paction is not None:
            all_key_actions.add(paction.func)
            if is_sequence:
                if trigger is not None:
                    key_definitions.append(KeyDefinition(True, paction, trigger[0], trigger[1], trigger[2], rest))
            else:
                assert key is not None
                key_definitions.append(KeyDefinition(False, paction, mods, is_native, key))


def parse_symbol_map(val: str) -> Dict[Tuple[int, int], str]:
    parts = val.split()
    symbol_map: Dict[Tuple[int, int], str] = {}

    def abort() -> Dict[Tuple[int, int], str]:
        log_error('Symbol map: {} is invalid, ignoring'.format(
            val))
        return {}

    if len(parts) < 2:
        return abort()
    family = ' '.join(parts[1:])

    def to_chr(x: str) -> int:
        if not x.startswith('U+'):
            raise ValueError()
        return int(x[2:], 16)

    for x in parts[0].split(','):
        a_, b_ = x.partition('-')[::2]
        b_ = b_ or a_
        try:
            a, b = map(to_chr, (a_, b_))
        except Exception:
            return abort()
        if b < a or max(a, b) > sys.maxunicode or min(a, b) < 1:
            return abort()
        symbol_map[(a, b)] = family
    return symbol_map


def parse_send_text_bytes(text: str) -> bytes:
    return python_string(text).encode('utf-8')


def parse_send_text(val: str, key_definitions: List[KeyDefinition]) -> None:
    parts = val.split(' ')

    def abort(msg: str) -> None:
        log_error('Send text: {} is invalid ({}), ignoring'.format(
            val, msg))

    if len(parts) < 3:
        return abort('Incomplete')
    mode, sc = parts[:2]
    text = ' '.join(parts[2:])
    key_str = '{} send_text {} {}'.format(sc, mode, text)
    parse_key(key_str, key_definitions)


SpecialHandlerFunc = Callable[[str, str, Dict[str, Any]], None]
special_handlers: Dict[str, SpecialHandlerFunc] = {}


def special_handler(func: SpecialHandlerFunc) -> SpecialHandlerFunc:
    special_handlers[func.__name__.partition('_')[2]] = func
    return func


def deprecated_handler(*names: str) -> Callable[[SpecialHandlerFunc], SpecialHandlerFunc]:
    def special_handler(func: SpecialHandlerFunc) -> SpecialHandlerFunc:
        for name in names:
            special_handlers[name] = func
        return func
    return special_handler


@special_handler
def handle_map(key: str, val: str, ans: Dict[str, Any]) -> None:
    parse_key(val, ans['key_definitions'])


@special_handler
def handle_symbol_map(key: str, val: str, ans: Dict[str, Any]) -> None:
    ans['symbol_map'].update(parse_symbol_map(val))


class FontFeature(str):

    def __new__(cls, name: str, parsed: bytes) -> 'FontFeature':
        ans: FontFeature = str.__new__(cls, name)  # type: ignore
        ans.parsed = parsed  # type: ignore
        return ans


@special_handler
def handle_font_features(key: str, val: str, ans: Dict[str, Any]) -> None:
    if val != 'none':
        parts = val.split()
        if len(parts) < 2:
            log_error("Ignoring invalid font_features {}".format(val))
        else:
            features = []
            for feat in parts[1:]:
                try:
                    parsed = defines.parse_font_feature(feat)
                except ValueError:
                    log_error('Ignoring invalid font feature: {}'.format(feat))
                else:
                    features.append(FontFeature(feat, parsed))
            if features:
                ans['font_features'][parts[0]] = tuple(features)


@special_handler
def handle_kitten_alias(key: str, val: str, ans: Dict[str, Any]) -> None:
    parts = val.split(maxsplit=2)
    if len(parts) >= 2:
        ans['kitten_aliases'][parts[0]] = parts[1:]


@special_handler
def handle_send_text(key: str, val: str, ans: Dict[str, Any]) -> None:
    # For legacy compatibility
    parse_send_text(val, ans['key_definitions'])


@special_handler
def handle_clear_all_shortcuts(key: str, val: str, ans: Dict[str, Any]) -> None:
    if to_bool(val):
        ans['key_definitions'] = [None]


@deprecated_handler('x11_hide_window_decorations', 'macos_hide_titlebar')
def handle_deprecated_hide_window_decorations_aliases(key: str, val: str, ans: Dict[str, Any]) -> None:
    if not hasattr(handle_deprecated_hide_window_decorations_aliases, key):
        setattr(handle_deprecated_hide_window_decorations_aliases, 'key', True)
        log_error('The option {} is deprecated. Use hide_window_decorations instead.'.format(key))
    if to_bool(val):
        if is_macos and key == 'macos_hide_titlebar' or (not is_macos and key == 'x11_hide_window_decorations'):
            ans['hide_window_decorations'] = True


@deprecated_handler('macos_show_window_title_in_menubar')
def handle_deprecated_macos_show_window_title_in_menubar_alias(key: str, val: str, ans: Dict[str, Any]) -> None:
    if not hasattr(handle_deprecated_macos_show_window_title_in_menubar_alias, key):
        setattr(handle_deprecated_macos_show_window_title_in_menubar_alias, 'key', True)
        log_error('The option {} is deprecated. Use macos_show_window_title_in menubar instead.'.format(key))
    macos_show_window_title_in = ans.get('macos_show_window_title_in', 'all')
    if to_bool(val):
        if macos_show_window_title_in == 'none':
            macos_show_window_title_in = 'menubar'
        elif macos_show_window_title_in == 'window':
            macos_show_window_title_in = 'all'
    else:
        if macos_show_window_title_in == 'all':
            macos_show_window_title_in = 'window'
        elif macos_show_window_title_in == 'menubar':
            macos_show_window_title_in = 'none'
    ans['macos_show_window_title_in'] = macos_show_window_title_in


@special_handler
def handle_env(key: str, val: str, ans: Dict[str, Any]) -> None:
    key, val = val.partition('=')[::2]
    key, val = key.strip(), val.strip()
    ans['env'][key] = expandvars(val, ans['env'])


def special_handling(key: str, val: str, ans: Dict[str, Any]) -> bool:
    func = special_handlers.get(key)
    if func is not None:
        func(key, val, ans)
        return True


def option_names_for_completion() -> Generator[str, None, None]:
    yield from defaults
    yield from special_handlers


def parse_config(lines: Iterable[str], check_keys: bool = True, accumulate_bad_lines: Optional[List[BadLine]] = None) -> Dict[str, Any]:
    ans: Dict[str, Any] = {
        'symbol_map': {}, 'keymap': {}, 'sequence_map': {}, 'key_definitions': [],
        'env': {}, 'kitten_aliases': {}, 'font_features': {}
    }
    defs: Optional[OptionsStub] = None
    if check_keys:
        defs = defaults

    parse_config_base(
        lines,
        defs,
        type_convert,
        special_handling,
        ans,
        check_keys=check_keys,
        accumulate_bad_lines=accumulate_bad_lines
    )
    return ans


def parse_defaults(lines: Iterable[str], check_keys: bool = False) -> Dict[str, Any]:
    ans = parse_config(lines, check_keys)
    return ans


xc = init_config(config_lines(all_options), parse_defaults)
Options: Type[OptionsStub] = xc[0]
defaults: OptionsStub = xc[1]
actions = frozenset(all_key_actions) | frozenset(
    'run_simple_kitten combine send_text goto_tab goto_layout set_font_size new_tab_with_cwd new_window_with_cwd new_os_window_with_cwd'.
    split()
)
no_op_actions = frozenset({'noop', 'no-op', 'no_op'})


def merge_configs(defaults: Dict, vals: Dict) -> Dict:
    ans = {}
    for k, v in defaults.items():
        if isinstance(v, dict):
            newvals = vals.get(k, {})
            ans[k] = merge_dicts(v, newvals)
        elif k == 'key_definitions':
            ans['key_definitions'] = v + vals.get('key_definitions', [])
        else:
            ans[k] = vals.get(k, v)
    return ans


def build_ansi_color_table(opts: OptionsStub = defaults) -> List[int]:

    def as_int(x: Tuple[int, int, int]) -> int:
        return (x[0] << 16) | (x[1] << 8) | x[2]

    def col(i: int) -> int:
        return as_int(getattr(opts, 'color{}'.format(i)))

    return list(map(col, range(256)))


def atomic_save(data: bytes, path: str) -> None:
    import tempfile
    fd, p = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.rename(p, path)
    finally:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
        except Exception as err:
            log_error('Failed to delete temp file {} for atomic save with error: {}'.format(
                p, err))


@contextmanager
def cached_values_for(name: str) -> Generator[Dict, None, None]:
    cached_path = os.path.join(cache_dir(), name + '.json')
    cached_values: Dict = {}
    try:
        with open(cached_path, 'rb') as f:
            cached_values.update(json.loads(f.read().decode('utf-8')))
    except FileNotFoundError:
        pass
    except Exception as err:
        log_error('Failed to load cached in {} values with error: {}'.format(
            name, err))

    yield cached_values

    try:
        data = json.dumps(cached_values).encode('utf-8')
        atomic_save(data, cached_path)
    except Exception as err:
        log_error('Failed to save cached values with error: {}'.format(
            err))


def commented_out_default_config() -> str:
    ans = []
    for line in as_conf_file(all_options.values()):
        if line and line[0] != '#':
            line = '# ' + line
        ans.append(line)
    return '\n'.join(ans)


def prepare_config_file_for_editing() -> str:
    if not os.path.exists(defconf):
        d = os.path.dirname(defconf)
        with suppress(FileExistsError):
            os.makedirs(d)
        with open(defconf, 'w', encoding='utf-8') as f:
            f.write(commented_out_default_config())
    return defconf


def finalize_keys(opts: OptionsStub) -> None:
    defns: List[KeyDefinition] = []
    for d in getattr(opts, 'key_definitions'):
        if d is None:  # clear_all_shortcuts
            defns = []
        else:
            defns.append(d)
    kitten_aliases: List[Dict[str, Sequence[str]]] = getattr(opts, 'kitten_aliases')
    for d in defns:
        d.resolve(opts.kitty_mod)
        if kitten_aliases and d.action.func == 'kitten':
            d.resolve_kitten_aliases(kitten_aliases)
    keymap: KeyMap = {}
    sequence_map: SequenceMap = {}

    for defn in defns:
        is_no_op = defn.action.func in no_op_actions
        if defn.is_sequence:
            keymap.pop(defn.trigger, None)
            s = sequence_map.setdefault(defn.trigger, {})
            if is_no_op:
                s.pop(defn.rest, None)
                if not s:
                    del sequence_map[defn.trigger]
            else:
                s[defn.rest] = defn.action
        else:
            sequence_map.pop(defn.trigger, None)
            if is_no_op:
                keymap.pop(defn.trigger, None)
            else:
                keymap[defn.trigger] = defn.action
    opts.keymap = keymap
    opts.sequence_map = sequence_map


def load_config(*paths: str, overrides: Optional[Iterable[str]] = None, accumulate_bad_lines: Optional[List[BadLine]] = None) -> OptionsStub:
    parser = parse_config
    if accumulate_bad_lines is not None:
        parser = partial(parse_config, accumulate_bad_lines=accumulate_bad_lines)
    opts = _load_config(Options, defaults, parser, merge_configs, *paths, overrides=overrides)
    finalize_keys(opts)
    if opts.background_opacity < 1.0 and opts.macos_titlebar_color:
        log_error('Cannot use both macos_titlebar_color and background_opacity')
        opts.macos_titlebar_color = 0
    return opts


class KittyCommonOpts(TypedDict):
    select_by_word_characters: str
    open_url_with: List[str]
    url_prefixes: Tuple[str, ...]


def common_opts_as_dict(opts: Optional[OptionsStub] = None) -> KittyCommonOpts:
    if opts is None:
        opts = defaults
    return {
        'select_by_word_characters': opts.select_by_word_characters,
        'open_url_with': opts.open_url_with,
        'url_prefixes': opts.url_prefixes,
    }
