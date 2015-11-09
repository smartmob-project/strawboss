# -*- coding: utf-8 -*-

import argparse
import pkg_resources
import sys

version = pkg_resources.resource_string('strawboss', 'version.txt')
if hasattr(version, 'decode'):
    version = version.decode('utf-8')

cli = argparse.ArgumentParser(description="Run programs.")
cli.add_argument('--version', dest='print_version', action='store_true',
                 default=False, help="Print version and exit.")

def main(arguments=None):
    if arguments is None:
        arguments = sys.argv[1:]
    arguments = cli.parse_args(arguments)
    if arguments.print_version:
        print(version)
        return
