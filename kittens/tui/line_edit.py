#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2018, Kovid Goyal <kovid at kovidgoyal.net>

from typing import Callable, Tuple

from kitty.fast_data_types import truncate_point_for_length, wcswidth
from kitty.key_encoding import RELEASE, KeyEvent, key_defs as K

HOME = K['HOME']
END = K['END']
BACKSPACE = K['BACKSPACE']
DELETE = K['DELETE']
LEFT = K['LEFT']
RIGHT = K['RIGHT']


class LineEdit:

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.current_input = ''
        self.cursor_pos = 0
        self.pending_bell = False

    def split_at_cursor(self, delta: int = 0) -> Tuple[str, str]:
        pos = max(0, self.cursor_pos + delta)
        x = truncate_point_for_length(self.current_input, pos) if pos else 0
        before, after = self.current_input[:x], self.current_input[x:]
        return before, after

    def write(self, write: Callable[[str], None], prompt: str = '') -> None:
        if self.pending_bell:
            write('\a')
            self.pending_bell = False
        write(prompt)
        write(self.current_input)
        write('\r\x1b[{}C'.format(self.cursor_pos + wcswidth(prompt)))

    def add_text(self, text: str) -> None:
        if self.current_input:
            x = truncate_point_for_length(self.current_input, self.cursor_pos) if self.cursor_pos else 0
            self.current_input = self.current_input[:x] + text + self.current_input[x:]
        else:
            self.current_input = text
        self.cursor_pos += wcswidth(text)

    def on_text(self, text: str, in_bracketed_paste: bool) -> None:
        self.add_text(text)

    def backspace(self, num: int = 1) -> bool:
        before, after = self.split_at_cursor()
        nbefore = before[:-num]
        if nbefore != before:
            self.current_input = nbefore + after
            self.cursor_pos = wcswidth(nbefore)
            return True
        self.pending_bell = True
        return False

    def delete(self, num: int = 1) -> bool:
        before, after = self.split_at_cursor()
        nafter = after[num:]
        if nafter != after:
            self.current_input = before + nafter
            self.cursor_pos = wcswidth(before)
            return True
        self.pending_bell = True
        return False

    def _left(self) -> None:
        if not self.current_input:
            self.cursor_pos = 0
            return
        if self.cursor_pos:
            before, after = self.split_at_cursor(-1)
            self.cursor_pos = wcswidth(before)

    def _right(self) -> None:
        if not self.current_input:
            self.cursor_pos = 0
            return
        max_pos = wcswidth(self.current_input)
        if self.cursor_pos >= max_pos:
            self.cursor_pos = max_pos
            return
        before, after = self.split_at_cursor(1)
        self.cursor_pos += 1 + int(wcswidth(before) == self.cursor_pos)

    def _move_loop(self, func: Callable[[], None], num: int) -> bool:
        before = self.cursor_pos
        changed = False
        while num > 0:
            func()
            changed = self.cursor_pos != before
            if not changed:
                break
            num -= 1
        if not changed:
            self.pending_bell = True
        return changed

    def left(self, num: int = 1) -> bool:
        return self._move_loop(self._left, num)

    def right(self, num: int = 1) -> bool:
        return self._move_loop(self._right, num)

    def home(self) -> bool:
        if self.cursor_pos:
            self.cursor_pos = 0
            return True
        return False

    def end(self) -> bool:
        orig = self.cursor_pos
        self.cursor_pos = wcswidth(self.current_input)
        return self.cursor_pos != orig

    def on_key(self, key_event: KeyEvent) -> bool:
        if key_event.type is RELEASE:
            return False
        elif key_event.key is HOME:
            return self.home()
        elif key_event.key is END:
            return self.end()
        elif key_event.key is BACKSPACE:
            self.backspace()
            return True
        elif key_event.key is DELETE:
            self.delete()
            return True
        elif key_event.key is LEFT:
            self.left()
            return True
        elif key_event.key is RIGHT:
            self.right()
            return True
        return False
