#!/usr/bin/env python

import os
import sys
import uuid
import hashlib
import logging
import argparse
import six
if six.PY2:
    import ConfigParser
else:
    from configparser import ConfigParser


BASE_PATH = os.path.dirname(os.path.realpath(__file__))


class FileHeuristicCache:
    def __init__(self, fn):
        """
        Construct an object that stores file comparison heuristics.
        :param filename of file
        """
        self.fn = fn
        self.hash = self.getHash()

    def __eq__(self, other):
        if self.hash == other.hash:
            return bool(self.hash)
        return False

    def __str__(self):
        return "<#%s#>" % self.fn

    def __repr__(self):
        return str(self)

    def __hash__(self):
        if self.hash is None:
            # if we can't hash contents, fall back to filename
            return hash(self.fn)
        return hash(self.hash)

    def getHash(self):
        """
        Calculate hash of file contents
        :return string, hash value or None if file doesn't exist
        """
        hashMethod = hashlib.sha256()

        def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
            for block in bytesiter:
                hasher.update(block)
            return (hasher.hexdigest() if ashexstr else hasher.digest())

        def file_as_blockiter(afile, blocksize=65536):
            with afile:
                block = afile.read(blocksize)
                while len(block) > 0:
                    yield block
                    block = afile.read(blocksize)

        if (os.path.exists(self.fn)):
            hash = hash_bytestr_iter(
                file_as_blockiter(open(self.fn, 'rb')), hashMethod, True)
            return hash
        return None


def main(args, config, loglevel):

    # current count of all files found in path
    filecount = 0
    # current count of duplicates found
    dupecount = 0
    # list of unique files
    filehash = dict()
    uniques = set()
    dupes = set()

    logging.info("Specified search path: %s" % args.searchpath)

    if os.path.exists(args.searchpath):
        logging.info('Found the supplied filepath: %s' % args.searchpath)

    # mega-lists of components for all child paths of search path
    for root, dirs, files in os.walk(args.searchpath):
        if not files:
            continue

        for f in files:
            filecount += 1  # sanity check
            fn = os.path.join(root, f)  # get full path
            candidate = FileHeuristicCache(fn)

            if candidate in uniques:
                logging.info('Dupe! - %s' % candidate.fn)
                logging.debug('Adding to hash with key ' + str(candidate.hash))
                logging.debug('Found: ' + str(filehash[candidate.hash]))
                (filehash[candidate.hash]).append(candidate)
                dupes.add(candidate.hash)
                dupecount += 1
            else:
                filehash[candidate.hash] = [candidate]
                logging.info('New file: ' + candidate.fn)
                logging.debug('Adding to hash with key ' + str(candidate.hash))

            uniques.add(candidate)  # Couldn't this be in the else above?

    logging.info(str(uniques))
    logging.info('Total file count: ' + str(filecount))
    logging.info('Total dupe count: ' + str(dupecount))
    logging.info('Total unique file count: ' + str(len(uniques)))

    for d in dupes:
        logging.info(str(d)+":"+str(filehash[d]))


def init_config():
    """
    Load configuration from config file
    :return config
    """
    config_logfilepath = os.path.join(BASE_PATH, 'dupeChecker.conf')

    if not os.path.exists(config_logfilepath):
        print('Config file not found: {}'.format(config_logfilepath))
        sys.exit(1)
    config = ConfigParser.SafeConfigParser()
    config.read(config_logfilepath)
    return config


def init_logging(config, loglevel):
    """
    Initialize basic logging functionality
    :param config
    :param loglevel
    """

    fmt = '%%(asctime)s [%s] %%(message)s' % str(uuid.uuid4())[:6]
    logfile = os.path.join(BASE_PATH, config.get('Logging', 'log-filename'))

    logging.basicConfig(level=loglevel,
                        format=fmt,
                        filename=logfile)

    console = logging.StreamHandler()
    console.setLevel(loglevel)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def init_parse_args():
    parser = argparse.ArgumentParser(
        description="Compares files in a given directory for \
                duplicates based on contents.",
        epilog="commandline like '%(prog)s @params.conf'.",
        fromfile_prefix_chars='@')

    parser.add_argument(
        "searchpath",
        help="supply path to check for duplicates",
        metavar="PATH")

    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true")

    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':

    config = init_config()
    args = init_parse_args()

    loglevel = logging.DEBUG if args.verbose else logging.INFO

    init_logging(config, loglevel)

    main(args, config, loglevel)

# Todo : add filter for EXIF creation time
# Todo : add filter for similar filename (like suffix)
# Todo : Exclusions, leave some files/filetypes out
# Todo : database for duplicates?
# Todo : Parallelize?
