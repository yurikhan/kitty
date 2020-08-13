Integrations with other tools
================================

kitty provides extremely powerful interfaces such as :doc:`remote-control` and
:doc:`kittens/custom` and :doc:`kittens/icat`
that allow it to be integrated with other tools seamlessly.


Image and document viewers
----------------------------

Powered by kitty's :doc:`graphics-protocol` there exist many tools for viewing
images and other types of documents directly in your terminal, even over SSH.

`termpdf.py <https://github.com/dsanson/termpdf.py>`_
    a terminal PDF/DJVU/CBR viewer

`mdcat <https://github.com/lunaryorn/mdcat>`_
    Display markdown files nicely formatted with images in the terminal

`ranger <https://github.com/ranger/ranger>`_
    a terminal file manager, with previews of file contents powered by kitty's graphics protocol.

`nnn <https://github.com/jarun/nnn/>`_
    another terminal file manager, with previews of file contents powered by kitty's graphics protocol.

`hunter <https://github.com/rabite0/hunter>`_
    another terminal file manager, with previews of file contents powered by kitty's graphics protocol.

`koneko <https://github.com/twenty5151/koneko>`_
    browse images from the pixiv artist community directly in kitty


System and data visualisation tools
---------------------------------------

`neofetch <https://github.com/dylanaraps/neofetch>`_
    A command line system information tool that shows images using kitty's graphics protocol

`matplotlib <https://github.com/jktr/matplotlib-backend-kitty>`_
    show matplotlib plots directly in kitty

`KittyTerminalImages.jl <https://github.com/simonschoelly/KittyTerminalImages.jl>`_
    show images from Julia directly in kitty

`gnuplot <http://www.gnuplot.info/>`_
    a graphing and data visualization tool that can be made to display its
    output in kitty with the following bash snippet::

        function iplot {
            cat <<EOF | gnuplot
            set terminal pngcairo enhanced font 'Fira Sans,10'
            set autoscale
            set samples 1000
            set output '|kitty +kitten icat --stdin yes'
            set object 1 rectangle from screen 0,0 to screen 1,1 fillcolor rgb"#fdf6e3" behind
            plot $@
            set output '/dev/null'
            EOF
        }

   Add this to bashrc and then to plot a function, simply do::

        iplot 'sin(x*3)*exp(x*.2)'


Editor integration
-----------------------

kitty can be integrated into many different terminal editors to add features
such a split windows, previews, REPLs etc.


`kakoune <https://kakoune.org/>`_
    integrates with kitty to use native kitty windows for its windows/panels and REPLs.

`vim-slime <https://github.com/jpalardy/vim-slime#kitty>`_
    uses kitty remote control for a Lisp REPL.

`vim-kitty-navigator <https://github.com/knubie/vim-kitty-navigator>`_
    allows you to navigate seamlessly between vim and kitty splits using a consistent set of hotkeys.

`vim-test <https://github.com/vim-test/vim-test>`_
    allows easily running tests in a terminal window


Scrollback manipulation
-------------------------

`kitty-search <https://github.com/trygveaa/kitty-kitten-search>`_
    Live incremental search of the scrollback buffer.

`kitty-grab <https://github.com/yurikhan/kitty_grab>`_
    keyboard based text selection for the kitty scrollback buffer.



Miscellaneous
------------------

`kitty-smart-tab <https://github.com/yurikhan/kitty-smart-tab>`_
    use keys to either control tabs or pass them onto running applications if
    no tabs are present

`kitty-smart-scroll <https://github.com/yurikhan/kitty-smart-scroll>`_
    use keys to either scroll or pass them onto running applications if
    no scrollback buffer is present

`reload keybindings <https://github.com/kovidgoyal/kitty/issues/1292#issuecomment-582388769>`_
    reload key bindings from :file:`kitty.conf` without needing to restart
    kitty

`kitti3 <https://github.com/LandingEllipse/kitti3>`_
    allow using kitty as a drop-down terminal under the i3 window manager

`weechat-hints <https://github.com/GermainZ/kitty-weechat-hints>`_
    URL hints kitten for WeeChat that works without having to use WeeChat's
    raw-mode.
