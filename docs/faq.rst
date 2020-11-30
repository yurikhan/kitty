Frequently Asked Questions
==============================

.. highlight:: sh

.. contents::

Some special symbols are rendered small/truncated in kitty?
-----------------------------------------------------------

The number of cells a unicode character takes up are controlled by the unicode
standard.  All characters are rendered in a single cell unless the unicode
standard says they should be rendered in two cells. When a symbol does not fit,
it will either be rescaled to be smaller or truncated (depending on how much
extra space it needs). This is often different from other terminals which just
let the character overflow into neighboring cells, which is fine if the
neighboring cell is empty, but looks terrible if it is not.

Some programs, like powerline, vim with fancy gutter symbols/status-bar, etc.
misuse unicode characters from the private use area to represent symbols. Often
these symbols are square and should be rendered in two cells.  However, since
private use area symbols all have their width set to one in the unicode
standard, |kitty| renders them either smaller or truncated. The exception is if
these characters are followed by a space or empty cell in which case kitty
makes use of the extra cell to render them in two cells.


Using a color theme with a background color does not work well in vim?
-----------------------------------------------------------------------

First make sure you have not changed the TERM environment variable, it should
be ``xterm-kitty``. vim uses *background color erase* even if the terminfo file
does not contain the ``bce`` capability. This is a bug in vim. You can work around
it by adding the following to your vimrc::

    let &t_ut=''

See :ref:`here <ext_styles>` for why |kitty| does not support background color erase.


I get errors about the terminal being unknown or opening the terminal failing when SSHing into a different computer?
-----------------------------------------------------------------------------------------------------------------------

This happens because the |kitty| terminfo files are not available on the server.
You can ssh in using the following command which will automatically copy the
terminfo files to the server::

    kitty +kitten ssh myserver

If for some reason that does not work (typically because the server is using a
non POSIX compliant shell), you can use the following one-liner instead (it
is slower as it needs to ssh into the server twice, but will work with most
servers)::

    infocmp xterm-kitty | ssh myserver tic -x -o \~/.terminfo /dev/stdin

If you are behind a proxy (like Balabit) that prevents this, you must redirect the
1st command to a file, copy that to the server and run ``tic`` manually.  If you
connect to a server, embedded or Android system that doesn't have ``tic``, copy over
your local file terminfo to the other system as :file:`~/.terminfo/x/xterm-kitty`.

Really, the correct solution for this is to convince the OpenSSH maintainers to
have ssh do this automatically, if possible, when connecting to a server, so that
all terminals work transparently.

If the server is running FreeBSD, or another system that relies on termcap
rather than terminfo, you will need to convert the terminfo file on your local
machine by running (on local machine with |kitty|)::

    infocmp -C xterm-kitty

The output of this command is the termcap description, which should be appended
to :file:`/usr/share/misc/termcap` on the remote server. Then run the following
command to apply your change (on the server)::

    cap_mkdb /usr/share/misc/termcap


Keys such as arrow keys, backspace, delete, home/end, etc. do not work when using su or sudo?
-------------------------------------------------------------------------------------------------

Make sure the TERM environment variable, is ``xterm-kitty``.  And either the
TERMINFO environment variable points to a directory containing :file:`x/xterm-kitty`
or that file is under :file:`~/.terminfo/x/`.

Note that ``sudo`` might remove TERMINFO.  Then setting it at the shell prompt can
be too late, because command line editing may not be reinitialized.  In that case
you can either ask ``sudo`` to set it or if that is not supported, insert an ``env``
command before starting the shell, or, if not possible, after sudo start another
Shell providing the right terminfo path::

    sudo … TERMINFO=$HOME/.terminfo bash -i
    sudo … env TERMINFO=$HOME/.terminfo bash -i
    TERMINFO=/home/ORIGINALUSER/.terminfo exec bash -i

You can configure sudo to preserve TERMINFO by running ``sudo
visudo`` and adding the following line::

    Defaults env_keep += "TERM TERMINFO"

If you have double width characters in your prompt, you may also need to
explicitly set a UTF-8 locale, like::

    export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8


How do I change the colors in a running kitty instance?
------------------------------------------------------------

You can either use the
`OSC terminal escape codes <https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Operating-System-Commands>`_
to set colors or you can define keyboard shortcuts to set colors, for example::

    map f1 set_colors --configured /path/to/some/config/file/colors.conf

Or you can enable :doc:`remote control <remote-control>` for |kitty| and use :ref:`at_set-colors`.
The shortcut mapping technique has the same syntax as the remote control
command, for details, see :ref:`at_set-colors`.

A list of pre-made color themes for kitty is available at:
`kitty-themes <https://github.com/dexpota/kitty-themes>`_

Examples of using OSC escape codes to set colors::

    Change the default foreground color:
    printf '\x1b]10;#ff0000\x1b\\'
    Change the default background color:
    printf '\x1b]11;blue\x1b\\'
    Change the cursor color:
    printf '\x1b]12;blue\x1b\\'
    Change the selection background color:
    printf '\x1b]17;blue\x1b\\'
    Change the selection foreground color:
    printf '\x1b]19;blue\x1b\\'
    Change the nth color (0 - 255):
    printf '\x1b]4;n;green\x1b\\'

You can use various syntaxes/names for color specifications in the above
examples. See `XParseColor <https://linux.die.net/man/3/xparsecolor>`_
for full details.

If a ``?`` is given rather than a color specification, kitty will respond
with the current value for the specified color.


How do I specify command line options for kitty on macOS?
---------------------------------------------------------------

Apple does not want you to use command line options with GUI applications. To
workaround that limitation, |kitty| will read command line options from the file
:file:`<kitty config dir>/macos-launch-services-cmdline` when it is launched
from the GUI, i.e. by clicking the |kitty| application icon or using ``open -a kitty``.
Note that this file is *only read* when running via the GUI.

You can, of course, also run |kitty| from a terminal with command line options, using:
:file:`/Applications/kitty.app/Contents/MacOS/kitty`.

And within |kitty| itself, you can always run |kitty| using just `kitty` as it
cleverly adds itself to the ``PATH``.


kitty is not able to use my favorite font?
---------------------------------------------

|kitty| achieves its stellar performance by caching alpha masks of each rendered
character on the GPU, so that every character needs to be rendered only once.
This means it is a strictly character cell based display.  As such it can use
only monospace fonts, since every cell in the grid has to be the same size.
Furthermore, it needs fonts to be freely resizable, so it does not support
bitmapped fonts.

If your font is not listed in ``kitty list-fonts`` it means that it is not
monospace or is a bitmapped font. On Linux you can list all monospace fonts with::

    fc-list : family spacing outline scalable | grep -e spacing=100 -e spacing=90 | grep -e outline=True | grep -e scalable=True

Note that the spacing property is calculated by fontconfig based on actual
glyph widths in the font. If for some reason fontconfig concludes your favorite
monospace font does not have ``spacing=100`` you can override it by using the
following :file:`~/.config/fontconfig/fonts.conf`::

    <?xml version="1.0"?>
    <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
    <fontconfig>
    <match target="font">
        <test name="family">
            <string>Your Font Family Name</string>
        </test>
        <edit name="spacing">
            <int>100</int>
        </edit>
    </match>
    </fontconfig>

After creating (or modifying) this file, you may need to run the following
command to rebuild your fontconfig cache::

    fc-cache -r

Then, the font will be available in ``kitty list-fonts``.


How can I assign a single global shortcut to bring up the kitty terminal?
-----------------------------------------------------------------------------

Bringing up applications on a single key press is the job of the window
manager/desktop environment. For ways to do it with kitty (or indeed any
terminal) in different environments,
see `here <https://github.com/kovidgoyal/kitty/issues/45>`_.


How do I map key presses in kitty to different keys in the terminal program?
--------------------------------------------------------------------------------------

This is accomplished by using ``map`` with :sc:`send_text <send_text>` in :file:`kitty.conf`.
For example::

    map alt+s send_text all \x13

This maps :kbd:`alt+s` to :kbd:`ctrl+s`. To figure out what bytes to use for
the :sc:`send_text <send_text>` you can use the ``showkey`` utility. Run::

    showkey -a

Then press the key you want to emulate. On macOS, this utility is currently not
available. The manual way to figure it out is:

    1. Look up your key's decimal value in the table at the bottom of `this
       page <http://ascii-table.com/ansi-escape-sequences.php>`_ or any
       ANSI escape sequence table. There are different modifiers for :kbd:`ctrl`,
       :kbd:`alt`, etc. For e.g., for :kbd:`ctrl+s`, find the ``S`` row and look at
       the third column value, ``19``.

    2. Convert the decimal value to hex with ``kitty +runpy "print(hex(19))"``.
       This shows the hex value, ``13`` in this case.

    3. Use ``\x(hexval)`` in your ``send_text`` command in kitty. So in this example, ``\x13``


I am using tmux and have a problem
--------------------------------------

First, terminal multiplexers are `a bad idea
<https://github.com/kovidgoyal/kitty/issues/391#issuecomment-638320745>`_, do
not use them, if at all possible. kitty contains features that do all of what
tmux does, but better, with the exception of remote persistence (:iss:`391`).
If you still want to use tmux, read on.

Image display will not work, see `tmux issue
<https://github.com/tmux/tmux/issues/1391>`_.

If you are using tmux with multiple terminals or you start it under one
terminal and then switch to another and these terminals have different TERM
variables, tmux will break. You will need to restart it as tmux does not
support multiple terminfo definitions.

Copying to clipboard via OSC 52 will not work, because tmux does not support
the extended version of that protocol, you will need to add ``no-append`` to
:opt:`clipboard_control` in kitty.conf.

If you use any of the advanced features that kitty has innovated, such as
styled underlines, desktop notifications, extended keyboard support, etc.
they may or may not work, depending on the whims of tmux's maintainer, your
version of tmux, etc.
