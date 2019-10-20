"""
This is a complex file-based memoization package.
Before running, you need to call `cache configure` from the command line
Its key distinguishing feature compared to standard memoization
Is that it is able to check for changes in called functions
(child functions)
It is transparent, in that metadata and the outputs of the function
are pickled in a readable format
It also has various optimizations to assist in work with large
file sizes, like hashing pandas data frames
If you instantiate a Cache object, you use a function as
a method of the class
That function also remains a regular function and does not need
to be memoized
It's still kludgy, but very handy

Use:
First, instantiate c = cache.Cache()
Then any registered func can be run: out = c.func(args)
This package does its best to search for all called child code but it
definitely does not work perfectly
For example most things called inside a class like RunScript don't
seem to stick
"""

import os
import time
from .metadata import determine_metadata, refactor_metadata_for_readability
from .initialize import directory, exclusion_list, globals_list
from .config import config_path, configure_report, get_config, write_configs
from .config import configure as configure_
from .utils.utils import pickle_read, pickle_dump, printn
from .utils.globalslist import new_globals
from .disk.operations import cache_to_disk, search_cache, purge_id_in_cache


class Cache(object):

    def __init__(self,
                 directory=directory,
                 exclusion_list=exclusion_list,
                 noisily=False,
                 configure=False):

        self.directory = directory
        self.exclusion_list = exclusion_list
        self.counter_path = os.path.join(self.directory, 'counter.pkl')
        self.noisily = noisily
        self.handle_configure(configure)

    def __getattr__(self, attr):
        return self.__get_global_handler(attr)

    def __get_global_handler(self, name):
        handler = self.__global_handler
        handler.__func__.func_name = name
        return handler

    def __global_handler(self,
                         *args,
                         move_file_in_position=None,
                         rerun=False,
                         **kwargs):

        func = self.__global_handler.__func__.func_name
        printn('-'*os.get_terminal_size().columns, self.noisily)
        printn('* Function: %s' % func, self.noisily)

        metadata = self.get_metadata(func, args, kwargs)

        id_ = self.locate_id(metadata, rerun)
        id_, output = self.load_id(id_)

        if not id_:
            was_archived = False
            id_, output = self.run_function(func,
                                            args,
                                            kwargs,
                                            metadata,
                                            move_file_in_position)
        else:
            was_archived = True

        setattr(self, '_meta_%s' % id_,  metadata)
        setattr(self, '_meta_%s_was_archived' % id_, was_archived)

        printn('%s\n' % ('-'*os.get_terminal_size().columns), self.noisily)

        return output

    def get_metadata(self, func, args, kwargs):
        metadata = determine_metadata(func, args, kwargs,
                                      self.exclusion_list, self.globals_list)
        printn('* Metadata: %s '
               % refactor_metadata_for_readability(metadata), self.noisily)
        printn('* (identified) Called functions: %s'
               % list(metadata['code'].keys()), self.noisily)

        return metadata

    def locate_id(self, metadata, purge):
        id_ = search_cache(self.directory, metadata)
        if id_ and purge:
            id_ = self.purge_id(id_)
        return id_

    def load_id(self, id_):
        try:
            output = pickle_read(os.path.join(self.directory,
                                              'output_%s.pkl' % id_))
            printn('* Cache found; loaded from ID %s' % id_, self.noisily)
            return id_, output
        except EOFError:
            print('%s: Ran out of input' % EOFError.__name__)
            self.purge_id(self, id_)
            id_, output = None, None
        except FileNotFoundError:
            id_, output = None, None
        return id_, output

    def run_function(self, func, args, kwargs, metadata,
                     move_file_in_position):
        printn('* Cache not found; running', self.noisily)
        output = self.globals_list[func](*args, **kwargs)
        id_ = '%s' % round(time.time()*1000000)
        printn('* Cache created with ID %s' % id_, self.noisily)
        output = cache_to_disk(self.directory, id_, metadata,
                               output, move_file_in_position)
        self.counter_update(id_)
        return id_, output

    def purge_id(self, id_):
        printn('* Cache purged with ID %s' % id_, self.noisily)
        id2_ = purge_id_in_cache(self.directory, id_)
        self.counter_pop(id_)
        return id2_

    def counter_update(self, id_):
        counter = pickle_read(self.counter_path)
        try:
            t = round(time.time()*1000000)
            counter[id_] = (counter[id_][0] + 1, t)
        except KeyError:
            counter[id_] = (1, round(time.time()*1000000))
        pickle_dump(counter, self.counter_path)

    def counter_pop(self, id_):
        counter = pickle_read(self.counter_path)
        del counter[id_]
        pickle_dump(counter, self.counter_path)

    def configure_report(self):
        configure_report(self.config_file)

    def configure(self):
        self.config_file = configure_(stash=True)
        self.globals_list = new_globals(self.config_file)

    def handle_configure(self, configure):
        if configure is False:
            # use defaults
            self.config_file = config_path()
            self.globals_list = globals_list
        elif configure is True:
            # prompt for configure
            self.configure()
        elif isinstance(configure, str):
            # read config from path
            self.config_file = configure
            self.globals_list = new_globals(configure)
        elif isinstance(configure, dict):
            # pass arguments directly in a dict,
            # and otherwise rely on defaults
            assert set(configure.keys()).issubset(
                set(['directory', 'registry', 'exclusion_list']))
            directory, registry, exclusions = get_config()
            if 'directory' in configure.keys():
                directory = configure['directory']
            if 'registry' in configure.keys():
                registry = configure['registry']
            if 'directory' in configure.keys():
                exclusions = configure['exclusion_list']
            self.config_file = config_path(stash=True)
            write_configs(self.config_file, directory, registry, exclusions)
            self.globals_list = new_globals(self.config_file)
        else:
            raise Exception('Invalid configure')
