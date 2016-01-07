strawboss -- local procfile runner
==================================


Description
-----------

This project is a command-line interface and a collections of utilities for
locally running all programs in a distributed system using a ``Procfile``.  See
`Smartmob RFC 1 -- Procfile
<http://smartmob-rfc.readthedocs.org/en/latest/1-procfile.html>`_.


Command-line Reference
----------------------

Run processes declared in a Procfile, forward output of all children to stdout.
When a process ends, it is automatically restarted.  To stop, press CTRL-C or
send SIGINT and wait for all children to end.

Killing this program using SIGKILL will also forcibly terminate all children.

Errors and warnings are sent to stderr.  You can filter these or send them to a
different file if you wish.

.. program:: strawboss

.. option:: --version

   Print version and exit.

.. option:: --help

   Print usage and exit.

.. option:: --scale process-type:count

   Override the number of processes of a specific process type.  The value of
   ``process-type`` must correspond to a process type declared in the Procfile.
   The value of ``count`` must be a non-negative integer.  When zero is used,
   no instances of the process type will be started.

   This option can be specified multiple times, once per process type.

   The special value ``*`` is accepted as a process type name.  When used, the
   count is applied to all processes.  For example, to start 2 of each process
   type in the Procfile without naming them, you can use
   ``strawboss --scale=*:2``.  You can also use this to start only a specific
   process type ``foo`` by using ``strawboss --scale=*:0 --scale=foo:1``.
   Order of the process types doesn't matter.

.. option:: --procfile path

   Override path to ``Procfile``.  Defaults to ``"Procfile"`` (in the current
   working directory).

.. option:: --envfile path

   Override path to "environment file".  Defaults to ``".env"`` (in the current
   working directory).  Can be specified multiple times if you wish to combine
   multiple environment files.  They are merged in order in which they are
   specified, so the precedence is low to high in case of conflicts.

.. option:: --no-env

   Do not load ``".env"``, even if it exists.  It is illegal to use both
   ``--no-env`` and ``--envfile`` in the same invocation.

.. option:: --utc

   Print timestamps in UTC.  Useful if you intend to merge these logs with
   other logs that are already in UTC.  Typically, you use this when you intend
   to forward the standard output over the network to a log aggregation
   service.


API reference
-------------

Some symbols are part of the package's public API in case they turn out to be
useful for other programs.

.. py:data:: strawboss.version

   The package's version, as a string.

.. autofunction:: strawboss.run_once
.. autofunction:: strawboss.run_and_respawn
.. autofunction:: strawboss.main

Contributing
------------

We welcome pull requests!  Please open up an issue on the `issue tracker`_ to
discuss, fork the project and then send in a pull request :-)

Feel free to add yourself to the ``CONTRIBUTORS`` file on your first pull
request!

.. _`issue tracker`: https://github.com/smartmob/strawboss/issues

License
-------

The source code and documentation is made available under an MIT license.  See
``LICENSE`` file for details.


Indexes and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
