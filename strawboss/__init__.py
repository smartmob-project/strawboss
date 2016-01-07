# -*- coding: utf-8 -*-

import argparse
import asyncio
import datetime
import dotenvfile
import itertools
import os
import pkg_resources
import procfile
import re
import shlex
import signal
import sys
import dateutil.tz


# TODO: move shlex.split into procfile parser.
# TOOD: make command environment a dict in procfile parser.


def now(utc=False):
    """Returns the current time.

    :param utc: If ``True``, returns a timezone-aware ``datetime`` object in
       UTC.  When ``False`` (the default), returns a naive ``datetime`` object
       in local time.
    :return: A ``datetime`` object representing the current time at the time of
       the call.
    """
    if utc:
        return datetime.datetime.utcnow().replace(tzinfo=dateutil.tz.tzutc())
    else:
        return datetime.datetime.now()


version = pkg_resources.resource_string('strawboss', 'version.txt')
"""Package version (as a dotted string)."""
version = version.decode('utf-8').strip()


class ListOverride(argparse.Action):
    """Similar to ``append`` action, but replaces default."""

    def __call__(self, parser, namespace, values, option_string):
        """Called once for each occurrence."""
        if getattr(namespace, self.dest) is self.default:
            setattr(namespace, self.dest, [values])
        else:
            getattr(namespace, self.dest).append(values)


def parse_scale(x):
    """Splits a "%s:%d" string and returns the string and number.

    :return: A ``(string, int)`` pair extracted from ``x``.

    :raise ValueError: the string ``x`` does not respect the input format.
    """
    match = re.match(r'^(.+?):(\d+)$', x)
    if not match:
        raise ValueError('Invalid scale "%s".' % x)
    return match.group(1), int(match.group(2))


def merge_envs(*args):
    """Union of one or more dictionaries.

    In case of duplicate keys, the values in the right-most arguments will
    squash (overwrite) the value provided by any dict preceding it.

    :param args: Sequence of ``dict`` objects that should be merged.
    :return: A ``dict`` containing the union of keys in all input dicts.

    """
    env = {}
    for arg in args:
        if not arg:
            continue
        env.update(arg)
    return env


@asyncio.coroutine
def run_once(name, cmd, env, shutdown, loop=None, utc=False):
    """Starts a child process and waits for its completion.

    Standard output and error streams are captured and forwarded to the parent
    process' standard output.  Each line is prefixed with the current time (as
    measured by the parent process) and the child process ``name``.

    :param name: Label for the child process.  Will be used as a prefix to all
       lines captured by this child process.
    :param cmd: Command-line that will be used to invoke the child process.
       Can be a string or sequence of strings.  When a string is passed,
       ``shlex.split()`` will be used to break it into a sequence of strings
       with smart quoting analysis.  If this does not give the intended
       results, break it down as you see fit and pass a sequence of strings.
    :param env: Environment variables that should be injected in the child
       process.  If ``None``, the parent's environment will be inherited as it.
       If a ``dict`` is provided, this will overwrite the entire environment;
       it is the caller's responsibility to merge this with the parent's
       environment if they see fit.
    :param shutdown: Future that the caller will fulfill to indicate that the
       process should be killed early.  When this is set, the process is sent
       SIGINT and then is let complete naturally.
    :param loop: Event loop to use.  When ``None``, the default event loop is
       used.
    :param utc: When ``True``, the timestamps are logged using the current time
       in UTC.
    """

    # Get the default event loop if necessary.
    loop = loop or asyncio.get_event_loop()

    # Launch the command into a child process.
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    process = yield from asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    print('%s [strawboss] %s(%d) spawned.' % (
        now(utc).isoformat(), name, process.pid
    ))

    # Exhaust the child's standard output stream.
    #
    # TODO: close stdin for new process.
    # TODO: terminate the process after the grace period.
    ready = asyncio.ensure_future(process.wait())
    pending = {shutdown, ready, process.stdout.readline()}
    while not ready.done():
        done, pending = yield from asyncio.wait(
            pending,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for future in done:
            # React to a request to shutdown the process.
            #
            # NOTE: shutdown is asynchronous unless the process completion
            #       notification is "in flight".  We forward the request to
            #       shutdown and then wait until the child process completes.
            if future is shutdown:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                else:
                    print('%s [strawboss] %s(%d) killed.' % (
                        now(utc).isoformat(), name, process.pid
                    ))
                continue
            # React to process death (natural, killed or terminated).
            if future is ready:
                exit_code = yield from future
                print('%s [strawboss] %s(%d) completed with exit status %d.' % (
                    now(utc).isoformat(), name, process.pid, exit_code
                ))
                continue
            # React to stdout having a full line of text.
            data = yield from future
            if not data:
                print('%s [strawboss] EOF from %s(%d).' % (
                    now(utc).isoformat(), name, process.pid,
                ))
                continue
            data = data.decode('utf-8').strip()
            print('%s [%s] %s' % (
                now(utc).isoformat(), name, data
            ))
            pending.add(process.stdout.readline())
    # Cancel any remaining tasks (e.g. readline).
    for future in pending:
        if future is shutdown:
            continue
        future.cancel()
    # Pass the exit code back to the caller.
    return exit_code


@asyncio.coroutine
def run_and_respawn(shutdown, loop=None, **kwds):
    """Starts a child process and respawns it every time it completes.

    :param shutdown: Future that the caller will fulfill to indicate that the
       process should not be respawned.  It is also passed to ``run_once()`` to
       indicate that the currently running process should be killed early.
    :param kwds: Arguments to pass to ``run_once()``.
    """

    # Get the default event loop if necessary.
    loop = loop or asyncio.get_event_loop()

    while not shutdown.done():
        t = loop.create_task(run_once(shutdown=shutdown, loop=loop, **kwds))
        yield from t


cli = argparse.ArgumentParser(description="Run programs.")
cli.add_argument('--version', action='version', version=version,
                 help="Print version and exit.")
cli.add_argument('--procfile', type=str, default='Procfile')
cli.add_argument('--envfile', type=str,
                 dest='envfiles', action=ListOverride, default=['.env'])
cli.add_argument('--no-env', dest='use_env',
                 action='store_false', default=True)
cli.add_argument('--utc', dest='use_utc',
                 action='store_true', default=False)
cli.add_argument('--scale', dest='scale', action='append', type=parse_scale,
                 default=[('*', 1)], help="Override number of instances.")


def main(arguments=None):
    """Command-line entry point.

    :param arguments: List of strings that contain the command-line arguments.
       When ``None``, the command-line arguments are looked up in ``sys.argv``
       (``sys.argv[0]`` is ignored).
    """

    # Parse command-line arguments.
    if arguments is None:
        arguments = sys.argv[1:]
    arguments = cli.parse_args(arguments)

    # Read the procfile.
    try:
        process_types = procfile.loadfile(arguments.procfile)
    except FileNotFoundError:
        sys.stderr.write('Procfile not found at "%s".' % arguments.procfile)
        sys.exit(2)

    # Read the env file(s).
    env = {}
    if arguments.use_env:
        for path in arguments.envfiles:
            try:
                env.update(dotenvfile.loadfile(path))
            except FileNotFoundError:
                sys.stderr.write(
                    'Warning: environment file "%s" not found.\n' % path
                )

    # Determine how many processes of each type we need.
    effective_scale = {}
    requested_scale = dict(arguments.scale)
    for label in process_types:
        effective_scale[label] = requested_scale.get(
            label,
            requested_scale['*'],
        )

    # Start the event loop.
    loop = asyncio.get_event_loop()

    # Register for shutdown events (idempotent, trap once only).
    shutdown = asyncio.Future()
    def stop_respawning():
        if shutdown.done():
            return
        shutdown.set_result(None)
        loop.remove_signal_handler(signal.SIGINT)
    loop.add_signal_handler(signal.SIGINT, stop_respawning)

    # Spawn tasks.
    tasks = []
    for label, count in effective_scale.items():
        process_type = process_types[label]
        the_cmd = shlex.split(process_type['cmd'])
        the_env = merge_envs(os.environ, env, process_type['env'])
        for i in range(count):
            task = loop.create_task(run_and_respawn(
                name='%s.%i' % (label, i),
                cmd=the_cmd,
                env=the_env,
                loop=loop,
                shutdown=shutdown,
                utc=arguments.use_utc,
            ))
            tasks.append(task)

    if not tasks:
        sys.stderr.write('Nothing to run.\n')
        sys.exit(2)

    # Wait for all tasks to complete.
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()


if __name__ == '__main__':  # pragma: no cover
    # Initialize logging for asyncio.
    import logging
    logging.basicConfig()

    # Proceed as requested :-)
    sys.exit(main(sys.argv[1:]))
