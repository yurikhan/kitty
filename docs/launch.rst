Launching programs in new windows/tabs
========================================

.. program:: launch


|kitty| has a :code:`launch` action that can be used to run arbitrary programs
in new windows/tabs. It can be mapped to user defined shortcuts in kitty.conf.
It is very powerful and allows sending the contents of
the current window to the launched program, as well as many other options.

In the simplest form, you can use it to open a new kitty window running the
shell, as shown below::

    map f1 launch

To run a different program simply pass the command line as arguments to
launch::

    map f1 launch vim path/to/some/file


To open a new window with the same working directory as the currently
active window::

    map f1 launch --cwd=current

To open the new window in a new tab::

    map f1 launch --type=tab

To pass the contents of the current screen and scrollback to the started process::

    map f1 launch --stdin-source=@screen_scrollback less

There are many more powerful options, refer to the complete list below.

The piping environment
--------------------------

When using :option:`launch --stdin-source`, the program to which the data is
piped has a special environment variable declared, ``KITTY_PIPE_DATA`` whose
contents are::

   KITTY_PIPE_DATA={scrolled_by}:{cursor_x},{cursor_y}:{lines},{columns}

where ``scrolled_by`` is the number of lines kitty is currently scrolled by,
``cursor_(x|y)`` is the position of the cursor on the screen with ``(1,1)``
being the top left corner and ``{lines},{columns}`` being the number of rows
and columns of the screen.


Special arguments
-------------------

There are a few special placeholder arguments that can be specified as part of
the command line. Namely ``@selection`` which is replaced by the current
selection and ``@active-kitty-window-id`` which is replaced by the id of the
currently active kitty window. For example::

    map f1 launch my-program @active-kitty-window-id


Watching launched windows
---------------------------

The :option:`launch --watcher` option allows you to specify python functions
that will be called at specific events, such as when the window is resized or
closed. Simply specify the path to a python module that specifies callback
functions for the events you are interested in, for example:

.. code-block:: python

    def on_resize(boss, window, data):
        # Here data will contain old_geometry and new_geometry

    def on_focus_change(boss, window, data):
        # Here data kill contain focused

    def on_close(boss, window, data):
        # called when window is closed, typically when the program running in
        # it exits.


Every callback is passed a reference to the global ``Boss`` object as well as
the ``Window`` object the action is occurring on. The ``data`` object is
mapping that contains event dependent data. Some useful methods and attributes
for the ``Window`` object are: ``as_text(as_ans=False, add_history=False,
add_wrap_markers=False, alternate_screen=False)`` with which you can get the
contents of the window and its scrollback buffer. Similarly,
``window.child.pid`` is the PID of the processes that was launched
in the window and ``window.id`` is the internal kitty ``id`` of the
window.


Syntax reference
------------------

.. include:: /generated/launch.rst
