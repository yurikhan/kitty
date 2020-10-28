#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

from kitty.fast_data_types import (
    DECAWM, DECCOLM, DECOM, IRM, Cursor, parse_bytes
)
from kitty.marks import marker_from_function, marker_from_regex

from . import BaseTest


class TestScreen(BaseTest):

    def test_draw_fast(self):
        s = self.create_screen()

        # Test in line-wrap, non-insert mode
        s.draw('a' * 5)
        self.ae(str(s.line(0)), 'a' * 5)
        self.ae(s.cursor.x, 5), self.ae(s.cursor.y, 0)
        s.draw('b' * 7)
        self.assertTrue(s.linebuf.is_continued(1))
        self.assertTrue(s.linebuf.is_continued(2))
        self.ae(str(s.line(0)), 'a' * 5)
        self.ae(str(s.line(1)), 'b' * 5)
        self.ae(str(s.line(2)), 'b' * 2)
        self.ae(s.cursor.x, 2), self.ae(s.cursor.y, 2)
        s.draw('c' * 15)
        self.ae(str(s.line(0)), 'b' * 5)
        self.ae(str(s.line(1)), 'bbccc')

        # Now test without line-wrap
        s.reset(), s.reset_dirty()
        s.reset_mode(DECAWM)
        s.draw('0123456789')
        self.ae(str(s.line(0)), '01239')
        self.ae(s.cursor.x, 5), self.ae(s.cursor.y, 0)
        s.draw('ab')
        self.ae(str(s.line(0)), '0123b')
        self.ae(s.cursor.x, 5), self.ae(s.cursor.y, 0)

        # Now test in insert mode
        s.reset(), s.reset_dirty()
        s.set_mode(IRM)
        s.draw('12345' * 5)
        s.cursor_back(5)
        self.ae(s.cursor.x, 0), self.ae(s.cursor.y, 4)
        s.reset_dirty()
        s.draw('ab')
        self.ae(str(s.line(4)), 'ab123')
        self.ae((s.cursor.x, s.cursor.y), (2, 4))

    def test_draw_char(self):
        # Test in line-wrap, non-insert mode
        s = self.create_screen()
        s.draw('ココx')
        self.ae(str(s.line(0)), 'ココx')
        self.ae(tuple(map(s.line(0).width, range(5))), (2, 0, 2, 0, 1))
        self.ae(s.cursor.x, 5), self.ae(s.cursor.y, 0)
        s.draw('ニチハ')
        self.ae(str(s.line(0)), 'ココx')
        self.ae(str(s.line(1)), 'ニチ')
        self.ae(str(s.line(2)), 'ハ')
        self.ae(s.cursor.x, 2), self.ae(s.cursor.y, 2)
        s.draw('Ƶ̧\u0308')
        self.ae(str(s.line(2)), 'ハƵ̧\u0308')
        self.ae(s.cursor.x, 3), self.ae(s.cursor.y, 2)
        s.draw('xy'), s.draw('\u0306')
        self.ae(str(s.line(2)), 'ハƵ̧\u0308xy\u0306')
        self.ae(s.cursor.x, 5), self.ae(s.cursor.y, 2)
        s.draw('c' * 15)
        self.ae(str(s.line(0)), 'ニチ')

        # Now test without line-wrap
        s.reset(), s.reset_dirty()
        s.reset_mode(DECAWM)
        s.draw('0\u030612345\u03066789\u0306')
        self.ae(str(s.line(0)), '0\u03061239\u0306')
        self.ae(s.cursor.x, 5), self.ae(s.cursor.y, 0)
        s.draw('ab\u0306')
        self.ae(str(s.line(0)), '0\u0306123b\u0306')
        self.ae(s.cursor.x, 5), self.ae(s.cursor.y, 0)

        # Now test in insert mode
        s.reset(), s.reset_dirty()
        s.set_mode(IRM)
        s.draw('1\u03062345' * 5)
        s.cursor_back(5)
        self.ae(s.cursor.x, 0), self.ae(s.cursor.y, 4)
        s.reset_dirty()
        s.draw('a\u0306b')
        self.ae(str(s.line(4)), 'a\u0306b1\u030623')
        self.ae((s.cursor.x, s.cursor.y), (2, 4))

    def test_emoji_skin_tone_modifiers(self):
        s = self.create_screen()
        q = chr(0x1f469) + chr(0x1f3fd)
        s.draw(q)
        self.ae(str(s.line(0)), q)
        self.ae(s.cursor.x, 2)

    def test_zwj(self):
        s = self.create_screen(cols=20)
        q = '\U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466'
        s.draw(q)
        self.ae(q, str(s.line(0)))
        self.ae(s.cursor.x, 8)

    def test_char_manipulation(self):
        s = self.create_screen()

        def init():
            s.reset(), s.reset_dirty()
            s.draw('abcde')
            s.cursor.bold = True
            s.cursor_back(4)
            s.reset_dirty()
            self.ae(s.cursor.x, 1)

        init()
        s.insert_characters(2)
        self.ae(str(s.line(0)), 'a  bc')
        self.assertTrue(s.line(0).cursor_from(1).bold)
        s.cursor_back(1)
        s.insert_characters(20)
        self.ae(str(s.line(0)), '')
        s.draw('xココ')
        s.cursor_back(5)
        s.reset_dirty()
        s.insert_characters(1)
        self.ae(str(s.line(0)), ' xコ')
        c = Cursor()
        c.italic = True
        s.line(0).apply_cursor(c, 0, 5)
        self.ae(s.line(0).width(2), 2)
        self.assertTrue(s.line(0).cursor_from(2).italic)
        self.assertFalse(s.line(0).cursor_from(2).bold)

        init()
        s.delete_characters(2)
        self.ae(str(s.line(0)), 'ade')
        self.assertTrue(s.line(0).cursor_from(4).bold)
        self.assertFalse(s.line(0).cursor_from(2).bold)

        init()
        s.erase_characters(2)
        self.ae(str(s.line(0)), 'a  de')
        self.assertTrue(s.line(0).cursor_from(1).bold)
        self.assertFalse(s.line(0).cursor_from(4).bold)
        s.erase_characters(20)
        self.ae(str(s.line(0)), 'a')

        init()
        s.erase_in_line()
        self.ae(str(s.line(0)), 'a')
        self.assertTrue(s.line(0).cursor_from(1).bold)
        self.assertFalse(s.line(0).cursor_from(0).bold)
        init()
        s.erase_in_line(1)
        self.ae(str(s.line(0)), '  cde')
        init()
        s.erase_in_line(2)
        self.ae(str(s.line(0)), '')
        init()
        s.erase_in_line(2, True)
        self.ae((False, False, False, False, False), tuple(map(lambda i: s.line(0).cursor_from(i).bold, range(5))))

    def test_erase_in_screen(self):
        s = self.create_screen()

        def init():
            s.reset()
            s.draw('12345' * 5)
            s.reset_dirty()
            s.cursor.x, s.cursor.y = 2, 1
            s.cursor.bold = True

        def all_lines(s):
            return tuple(str(s.line(i)) for i in range(s.lines))

        def continuations(s):
            return tuple(s.line(i).is_continued() for i in range(s.lines))

        init()
        s.erase_in_display(0)
        self.ae(all_lines(s), ('12345', '12', '', '', ''))
        self.ae(continuations(s), (False, True, False, False, False))

        init()
        s.erase_in_display(1)
        self.ae(all_lines(s), ('', '   45', '12345', '12345', '12345'))
        self.ae(continuations(s), (False, False, True, True, True))

        init()
        s.erase_in_display(2)
        self.ae(all_lines(s), ('', '', '', '', ''))
        self.assertTrue(s.line(0).cursor_from(1).bold)
        self.ae(continuations(s), (False, False, False, False, False))

        init()
        s.erase_in_display(2, True)
        self.ae(all_lines(s), ('', '', '', '', ''))
        self.ae(continuations(s), (False, False, False, False, False))
        self.assertFalse(s.line(0).cursor_from(1).bold)

    def test_cursor_movement(self):
        s = self.create_screen()
        s.draw('12345' * 5)
        s.reset_dirty()
        s.cursor_up(2)
        self.ae((s.cursor.x, s.cursor.y), (4, 2))
        s.cursor_up1()
        self.ae((s.cursor.x, s.cursor.y), (0, 1))
        s.cursor_forward(3)
        self.ae((s.cursor.x, s.cursor.y), (3, 1))
        s.cursor_back()
        self.ae((s.cursor.x, s.cursor.y), (2, 1))
        s.cursor_down()
        self.ae((s.cursor.x, s.cursor.y), (2, 2))
        s.cursor_down1(5)
        self.ae((s.cursor.x, s.cursor.y), (0, 4))

        s = self.create_screen()
        s.draw('12345' * 5)
        s.index()
        self.ae(str(s.line(4)), '')
        for i in range(4):
            self.ae(str(s.line(i)), '12345')
        s.draw('12345' * 5)
        s.cursor_up(5)
        s.reverse_index()
        self.ae(str(s.line(0)), '')
        for i in range(1, 5):
            self.ae(str(s.line(i)), '12345')

    def test_backspace_wide_characters(self):
        s = self.create_screen()
        s.draw('⛅')
        self.ae(s.cursor.x, 2)
        s.backspace()
        s.draw(' ')
        s.backspace()
        self.ae(s.cursor.x, 1)

    def test_resize(self):
        s = self.create_screen(scrollback=6)
        s.draw(''.join([str(i) * s.columns for i in range(s.lines)]))
        s.resize(3, 10)
        self.ae(str(s.line(0)), '0'*5 + '1'*5)
        self.ae(str(s.line(1)), '2'*5 + '3'*5)
        self.ae(str(s.line(2)), '4'*5)
        s.resize(5, 1)
        self.ae(str(s.line(0)), '4')
        self.ae(str(s.historybuf), '3\n3\n3\n3\n3\n2')
        s = self.create_screen(scrollback=20)
        s.draw(''.join(str(i) * s.columns for i in range(s.lines*2)))
        self.ae(str(s.linebuf), '55555\n66666\n77777\n88888\n99999')
        s.resize(5, 2)
        self.ae(str(s.linebuf), '88\n88\n99\n99\n9')

    def test_cursor_after_resize(self):

        def draw(text, end_line=True):
            s.draw(text)
            if end_line:
                s.linefeed(), s.carriage_return()

        s = self.create_screen()
        draw('123'), draw('123')
        y_before = s.cursor.y
        s.resize(s.lines, s.columns-1)
        self.ae(y_before, s.cursor.y)

        s = self.create_screen(cols=5, lines=8)
        draw('one')
        draw('two three four five |||', end_line=False)
        s.resize(s.lines + 2, s.columns + 2)
        y = s.cursor.y
        self.assertIn('|', str(s.line(y)))

        s = self.create_screen()
        draw('a')
        x_before = s.cursor.x
        s.resize(s.lines - 1, s.columns)
        self.ae(x_before, s.cursor.x)

    def test_tab_stops(self):
        # Taken from vttest/main.c
        s = self.create_screen(cols=80, lines=2)
        s.cursor_position(1, 1)
        s.clear_tab_stop(3)
        for col in range(1, s.columns - 1, 3):
            s.cursor_forward(3)
            s.set_tab_stop()
        s.cursor_position(1, 4)
        for col in range(4, s.columns - 1, 6):
            s.clear_tab_stop(0)
            s.cursor_forward(6)
        s.cursor_position(1, 7)
        s.clear_tab_stop(2)
        s.cursor_position(1, 1)
        for col in range(1, s.columns - 1, 6):
            s.tab()
            s.draw('*')
        s.cursor_position(2, 2)
        self.ae(str(s.line(0)), '\t*'*13)

    def test_margins(self):
        # Taken from vttest/main.c
        s = self.create_screen(cols=80, lines=24)

        def nl():
            s.carriage_return(), s.linefeed()

        for deccolm in (False, True):
            if deccolm:
                s.resize(24, 132)
                s.set_mode(DECCOLM)
            else:
                s.reset_mode(DECCOLM)
            region = s.lines - 6
            s.set_margins(3, region + 3)
            s.set_mode(DECOM)
            for i in range(26):
                ch = chr(ord('A') + i)
                which = i % 4
                if which == 0:
                    s.cursor_position(region + 1, 1), s.draw(ch)
                    s.cursor_position(region + 1, s.columns), s.draw(ch.lower())
                    nl()
                elif which == 1:
                    # Simple wrapping
                    s.cursor_position(region, s.columns), s.draw(chr(ord('A') + i - 1).lower() + ch)
                    # Backspace at right margin
                    s.cursor_position(region + 1, s.columns), s.draw(ch), s.backspace(), s.draw(ch.lower())
                    nl()
                elif which == 2:
                    # Tab to right margin
                    s.cursor_position(region + 1, s.columns), s.draw(ch), s.backspace(), s.backspace(), s.tab(), s.tab(), s.draw(ch.lower())
                    s.cursor_position(region + 1, 2), s.backspace(), s.draw(ch), nl()
                else:
                    s.cursor_position(region + 1, 1), nl()
                    s.cursor_position(region, 1), s.draw(ch)
                    s.cursor_position(region, s.columns), s.draw(ch.lower())
            for ln in range(2, region + 2):
                c = chr(ord('I') + ln - 2)
                before = '\t' if ln % 4 == 0 else ' '
                self.ae(c + ' ' * (s.columns - 3) + before + c.lower(), str(s.line(ln)))
            s.reset_mode(DECOM)
        # Test that moving cursor outside the margins works as expected
        s = self.create_screen(10, 10)
        s.set_margins(4, 6)
        s.cursor_position(0, 0)
        self.ae(s.cursor.y, 0)
        nl()
        self.ae(s.cursor.y, 1)
        s.cursor.y = s.lines - 1
        self.ae(s.cursor.y, 9)
        s.reverse_index()
        self.ae(s.cursor.y, 8)

    def test_sgr(self):
        s = self.create_screen()
        s.select_graphic_rendition(0, 1, 37, 42)
        s.draw('a')
        c = s.line(0).cursor_from(0)
        self.assertTrue(c.bold)
        self.ae(c.bg, (2 << 8) | 1)
        s.cursor_position(2, 1)
        s.select_graphic_rendition(0, 35)
        s.draw('b')
        c = s.line(1).cursor_from(0)
        self.ae(c.fg, (5 << 8) | 1)
        self.ae(c.bg, 0)
        s.cursor_position(2, 2)
        s.select_graphic_rendition(38, 2, 99, 1, 2, 3)
        s.draw('c')
        c = s.line(1).cursor_from(1)
        self.ae(c.fg, (1 << 24) | (2 << 16) | (3 << 8) | 2)

    def test_cursor_hidden(self):
        s = self.create_screen()
        s.toggle_alt_screen()
        s.cursor_visible = False
        s.toggle_alt_screen()
        self.assertFalse(s.cursor_visible)

    def test_dirty_lines(self):
        s = self.create_screen()
        self.assertFalse(s.linebuf.dirty_lines())
        s.draw('a' * (s.columns * 2))
        self.ae(s.linebuf.dirty_lines(), [0, 1])
        self.assertFalse(s.historybuf.dirty_lines())
        while not s.historybuf.count:
            s.draw('a' * (s.columns * 2))
        self.ae(s.historybuf.dirty_lines(), list(range(s.historybuf.count)))
        self.ae(s.linebuf.dirty_lines(), list(range(s.lines)))
        s.cursor.x, s.cursor.y = 0, 1
        s.insert_lines(2)
        self.ae(s.linebuf.dirty_lines(), [0, 3, 4])
        s.draw('a' * (s.columns * s.lines))
        self.ae(s.linebuf.dirty_lines(), list(range(s.lines)))
        s.cursor.x, s.cursor.y = 0, 1
        s.delete_lines(2)
        self.ae(s.linebuf.dirty_lines(), [0, 1, 2])

        s = self.create_screen()
        self.assertFalse(s.linebuf.dirty_lines())
        s.erase_in_line(0, False)
        self.ae(s.linebuf.dirty_lines(), [0])
        s.index(), s.index()
        s.erase_in_display(0, False)
        self.ae(s.linebuf.dirty_lines(), [0, 2, 3, 4])

        s = self.create_screen()
        self.assertFalse(s.linebuf.dirty_lines())
        s.insert_characters(2)
        self.ae(s.linebuf.dirty_lines(), [0])
        s.cursor.y = 1
        s.delete_characters(2)
        self.ae(s.linebuf.dirty_lines(), [0, 1])
        s.cursor.y = 2
        s.erase_characters(2)
        self.ae(s.linebuf.dirty_lines(), [0, 1, 2])

    def test_selection_as_text(self):
        s = self.create_screen()
        for i in range(2 * s.lines):
            if i != 0:
                s.carriage_return(), s.linefeed()
            s.draw(str(i) * s.columns)
        s.start_selection(0, 0)
        s.update_selection(4, 4)
        expected = ('55555', '\n66666', '\n77777', '\n88888', '\n99999')
        self.ae(s.text_for_selection(), expected)
        s.scroll(2, True)
        self.ae(s.text_for_selection(), expected)

    def test_variation_selectors(self):
        s = self.create_screen()
        s.draw('\U0001f610')
        self.ae(s.cursor.x, 2)
        s.carriage_return(), s.linefeed()
        s.draw('\U0001f610\ufe0e')
        self.ae(s.cursor.x, 1)
        s.carriage_return(), s.linefeed()
        s.draw('\u25b6')
        self.ae(s.cursor.x, 1)
        s.carriage_return(), s.linefeed()
        s.draw('\u25b6\ufe0f')
        self.ae(s.cursor.x, 2)

    def test_serialize(self):
        from kitty.window import as_text
        s = self.create_screen()
        s.draw('ab' * s.columns)
        s.carriage_return(), s.linefeed()
        s.draw('c')

        self.ae(as_text(s), 'ababababab\nc\n\n')
        self.ae(as_text(s, True), '\x1b[mababa\x1b[mbabab\n\x1b[mc\n\n')

        s = self.create_screen(cols=2, lines=2, scrollback=2)
        for i in range(1, 7):
            s.select_graphic_rendition(30 + i)
            s.draw(f'{i}' * s.columns)
        self.ae(as_text(s, True, True), '\x1b[m\x1b[31m11\x1b[m\x1b[32m22\x1b[m\x1b[33m33\x1b[m\x1b[34m44\x1b[m\x1b[m\x1b[35m55\x1b[m\x1b[36m66')

        def set_link(url=None, id=None):
            parse_bytes(s, '\x1b]8;id={};{}\x1b\\'.format(id or '', url or '').encode('utf-8'))

        s = self.create_screen()
        s.draw('a')
        set_link('moo', 'foo')
        s.draw('bcdef')
        self.ae(as_text(s, True), '\x1b[ma\x1b]8;id=foo;moo\x1b\\bcde\x1b[mf\n\n\n\x1b]8;;\x1b\\')
        set_link()
        s.draw('gh')
        self.ae(as_text(s, True), '\x1b[ma\x1b]8;id=foo;moo\x1b\\bcde\x1b[mf\x1b]8;;\x1b\\gh\n\n\n')
        s = self.create_screen()
        s.draw('a')
        set_link('moo')
        s.draw('bcdef')
        self.ae(as_text(s, True), '\x1b[ma\x1b]8;;moo\x1b\\bcde\x1b[mf\n\n\n\x1b]8;;\x1b\\')

    def test_pagerhist(self):
        hsz = 8
        s = self.create_screen(cols=2, lines=2, scrollback=2, options={'scrollback_pager_history_size': hsz})

        def contents():
            return s.historybuf.pagerhist_as_text()

        def line(i):
            q.append('\x1b[m' + f'{i}' * s.columns + '\r')

        def w(x):
            s.historybuf.pagerhist_write(x)

        def test():
            expected = ''.join(q)
            maxlen = hsz
            extra = len(expected) - maxlen
            if extra > 0:
                expected = expected[extra:]
            got = contents()
            self.ae(got, expected)

        q = []
        for i in range(4):
            s.draw(f'{i}' * s.columns)
        self.ae(contents(), '')
        s.draw('4' * s.columns), line(0), test()
        s.draw('5' * s.columns), line(1), test()
        s.draw('6' * s.columns), line(2), test()
        s.draw('7' * s.columns), line(3), test()
        s.draw('8' * s.columns), line(4), test()
        s.draw('9' * s.columns), line(5), test()

        s = self.create_screen(options={'scrollback_pager_history_size': 2048})
        text = '\x1b[msoft\r\x1b[mbreak\nnext😼cat'
        w(text)
        self.ae(contents(), text + '\n')
        s.historybuf.pagerhist_rewrap(2)
        self.ae(contents(), '\x1b[mso\rft\x1b[m\rbr\rea\rk\nne\rxt\r😼\rca\rt\n')

        s = self.create_screen(options={'scrollback_pager_history_size': 8})
        w('😼')
        self.ae(contents(), '😼\n')
        w('abcd')
        self.ae(contents(), '😼abcd\n')
        w('e')
        self.ae(contents(), 'abcde\n')

    def test_user_marking(self):

        def cells(*a, y=0, mark=3):
            return [(x, y, mark) for x in a]

        s = self.create_screen()
        s.draw('abaa')
        s.carriage_return(), s.linefeed()
        s.draw('xyxyx')
        s.set_marker(marker_from_regex('a', 3))
        self.ae(s.marked_cells(), cells(0, 2, 3))
        s.set_marker()
        self.ae(s.marked_cells(), [])

        def mark_x(text):
            col = 0
            for i, c in enumerate(text):
                if c == 'x':
                    col += 1
                    yield i, i, col

        s.set_marker(marker_from_function(mark_x))
        self.ae(s.marked_cells(), [(0, 1, 1), (2, 1, 2), (4, 1, 3)])
        s = self.create_screen(lines=5, scrollback=10)
        for i in range(15):
            s.draw(str(i))
            if i != 14:
                s.carriage_return(), s.linefeed()
        s.set_marker(marker_from_regex(r'\d+', 3))
        for i in range(10):
            self.assertTrue(s.scroll_to_next_mark())
            self.ae(s.scrolled_by, i + 1)
        self.ae(s.scrolled_by, 10)
        for i in range(10):
            self.assertTrue(s.scroll_to_next_mark(0, False))
            self.ae(s.scrolled_by, 10 - i - 1)
        self.ae(s.scrolled_by, 0)

        s = self.create_screen()
        s.draw('🐈ab')
        s.set_marker(marker_from_regex('🐈', 3))
        self.ae(s.marked_cells(), cells(0, 1))
        s.set_marker(marker_from_regex('🐈a', 3))
        self.ae(s.marked_cells(), cells(0, 1, 2))
        s.set_marker(marker_from_regex('a', 3))
        self.ae(s.marked_cells(), cells(2))
        s = self.create_screen(cols=20)
        s.tab()
        s.draw('ab')
        s.set_marker(marker_from_regex('a', 3))
        self.ae(s.marked_cells(), cells(8))
        s.set_marker(marker_from_regex('\t', 3))
        self.ae(s.marked_cells(), cells(*range(8)))

    def test_hyperlinks(self):
        s = self.create_screen()
        self.ae(s.line(0).hyperlink_ids(), tuple(0 for x in range(s.columns)))

        def set_link(url=None, id=None):
            parse_bytes(s, '\x1b]8;id={};{}\x1b\\'.format(id or '', url or '').encode('utf-8'))

        set_link('url-a', 'a')
        self.ae(s.line(0).hyperlink_ids(), tuple(0 for x in range(s.columns)))
        s.draw('a')
        self.ae(s.line(0).hyperlink_ids(), (1,) + tuple(0 for x in range(s.columns - 1)))
        s.draw('bc')
        self.ae(s.line(0).hyperlink_ids(), (1, 1, 1, 0, 0))
        set_link()
        s.draw('d')
        self.ae(s.line(0).hyperlink_ids(), (1, 1, 1, 0, 0))
        set_link('url-a', 'a')
        s.draw('efg')
        self.ae(s.line(0).hyperlink_ids(), (1, 1, 1, 0, 1))
        self.ae(s.line(1).hyperlink_ids(), (1, 1, 0, 0, 0))
        set_link('url-b')
        s.draw('hij')
        self.ae(s.line(1).hyperlink_ids(), (1, 1, 2, 2, 2))
        set_link()
        self.ae([('a:url-a', 1), (':url-b', 2)], s.hyperlinks_as_list())
        s.garbage_collect_hyperlink_pool()
        self.ae([('a:url-a', 1), (':url-b', 2)], s.hyperlinks_as_list())
        for i in range(s.lines + 2):
            s.linefeed()
        s.garbage_collect_hyperlink_pool()
        self.ae([('a:url-a', 1), (':url-b', 2)], s.hyperlinks_as_list())
        for i in range(s.lines * 2):
            s.linefeed()
        s.garbage_collect_hyperlink_pool()
        self.assertFalse(s.hyperlinks_as_list())
        set_link('url-a', 'x')
        s.draw('a')
        set_link('url-a', 'y')
        s.draw('a')
        set_link()
        self.ae([('x:url-a', 1), ('y:url-a', 2)], s.hyperlinks_as_list())

        s = self.create_screen()
        set_link('u' * 2048)
        s.draw('a')
        self.ae([(':' + 'u' * 2045, 1)], s.hyperlinks_as_list())
        s = self.create_screen()
        set_link('u' * 2048, 'i' * 300)
        s.draw('a')
        self.ae([('i'*256 + ':' + 'u' * (2045 - 256), 1)], s.hyperlinks_as_list())

        s = self.create_screen()
        set_link('1'), s.draw('1')
        set_link('2'), s.draw('2')
        set_link('3'), s.draw('3')
        s.cursor.x = 1
        set_link(), s.draw('X')
        self.ae(s.line(0).hyperlink_ids(), (1, 0, 3, 0, 0))
        self.ae([(':1', 1), (':2', 2), (':3', 3)], s.hyperlinks_as_list())
        s.garbage_collect_hyperlink_pool()
        self.ae([(':1', 1), (':3', 2)], s.hyperlinks_as_list())
        set_link('3'), s.draw('3')
        self.ae([(':1', 1), (':3', 2)], s.hyperlinks_as_list())
        set_link('4'), s.draw('4')
        self.ae([(':1', 1), (':3', 2), (':4', 3)], s.hyperlinks_as_list())

        s = self.create_screen()
        set_link('1'), s.draw('1')
        set_link('2'), s.draw('2')
        set_link('1'), s.draw('1')
        self.ae([(':2', 2), (':1', 1)], s.hyperlinks_as_list())

        s = self.create_screen()
        set_link('1'), s.draw('12'), set_link(), s.draw('X'), set_link('1'), s.draw('3')
        s.linefeed(), s.carriage_return()
        s.draw('abc')
        s.linefeed(), s.carriage_return()
        set_link(), s.draw('Z ')
        set_link('1'), s.draw('xyz')
        s.linefeed(), s.carriage_return()
        set_link('2'), s.draw('Z Z')
        self.assertIsNone(s.current_url_text())
        self.assertIsNone(s.hyperlink_at(0, 4))
        self.assertIsNone(s.current_url_text())
        self.ae(s.hyperlink_at(0, 0), '1')
        self.ae(s.current_url_text(), '123abcxyz')
        self.ae('1', s.hyperlink_at(3, 2))
        self.ae(s.current_url_text(), '123abcxyz')
        self.ae('2', s.hyperlink_at(1, 3))
        self.ae(s.current_url_text(), 'Z Z')
