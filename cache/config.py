import csv
import importlib
import os
import pkgutil
import itertools
import warnings
from collections import OrderedDict
from .utils import single_item, listr


def configure():
    """
    Top level configuraiton script
    Reads in existing file, prompts for new configuration,
    and spits out config.txt
    """
    config_file, dir_def, modules_def, exclusions_def = config_defaults()
    packages_def, modules_def = get_default_package_info(modules_def)
    cache_directory, packages, ask_submodules, exclusions = user_prompts(
        dir_def, packages_def, exclusions_def)
    use_submodules = prompt_submodules(
        listr(packages), ask_submodules, modules_def)
    write_configs(
        config_file, cache_directory, use_submodules, listr(exclusions))
    print('Configuration file saved to %s' % config_file)


def config_defaults():
    """
    Reads in the configuration file, if it exists, and returns those values
    as defaults
    """
    dirname = os.path.dirname(__file__)
    config_file = os.path.join(
        os.path.abspath(os.path.join(dirname, '..', 'config')), 'config.txt')
    if os.path.exists(config_file):
        dir_def, modules_def, exclusions_def = load_config(config_file)
    else:
        (dir_def, modules_def, exclusions_def) = ('None', 'None', 'None')
    return config_file, dir_def, modules_def, exclusions_def


def load_config(config_file):
    """
    Loads and parses the configuration text file
    """
    with open(config_file, 'r') as f:
        reader = csv.reader(f)
        config_dets = list(reader)
        config_dets = list(itertools.chain.from_iterable(config_dets))
        idx1 = config_dets.index('Cache Directory:')
        idx2 = config_dets.index('Import Modules:')
        idx3 = config_dets.index('Exclusions:')
        dir_def = single_item(config_dets[idx1+1:idx2])
        packages_def = config_dets[idx2+1:idx3]
        exclusions_def = config_dets[idx3+1:]
    return dir_def, packages_def, exclusions_def


def get_default_package_info(modules_def):
    """
    The configuration file lists modules and submodules. Gets top-level
    package information if it exists, and if not, returns empty defaults
    """
    if modules_def != 'None':
        packages_def = list(OrderedDict.fromkeys(
            [x.split('.')[0] for x in modules_def])) if isinstance(
                modules_def, list) else modules_def
        modules_def_dict = {module: 'y' for module in modules_def}
        return packages_def, modules_def_dict
    return 'None', {}


def user_prompts(dir_def, packages_def, exclusions_def):
    """
    Configuration prompt questions
    """
    cache_directory = user_prompt('Default directory for storing cache'
                                  ' files', dir_def)
    packages = user_prompt('List of user-written packages to register,'
                           ' separated by commas: ', packages_def)
    ask_submodules = user_prompt('Prompt to include all submodules '
                                 '(y/n)? ', inlist=['y', 'n'])
    exclusions = user_prompt('List of functions or modules to exclude '
                             'from code tree (rarely used)', exclusions_def)
    return cache_directory, packages, ask_submodules, exclusions


def user_prompt(prompt_string, default=None, inlist=None):
    """
    Takes a prompt string, and asks user for answer
        sets a default value if there is one
        keeps prompting if the value isn't in inlist
        splits a string list with commas into a list
    """
    prompt_string = '%s [%s]: ' % (
        prompt_string, default) if default else prompt_string
    output = input(prompt_string)
    output = default if output == '' else output
    if inlist:
        assert isinstance(inlist, list)
        while output not in inlist:
            output = input(prompt_string)
    output = [x.strip() for x in output.split(',')] if (
        isinstance(output, str) and ',' in output) else output
    return output


def prompt_submodules(packages, ask_submodules, modules_def):
    """
    First gets all submodules in the requested packages
    If user says to query about submodules, will list all of them
    out with defaults and ask for inclusion or exclusion (y/n)
    If not, will keep all the defaults, unless there are no
    submodules specified at all, in which case it will import
    all submodules in all packages the user specified
    and give a warning
    """
    submodules = []
    for package_name in packages:
        submodules = submodules + list_all_submodules(package_name)
    defaults = {module: ('n' if module not in modules_def.keys()
                else modules_def[module]) for module in submodules}
    if ask_submodules == 'y':
        use_submodules = submodules_prompts(submodules, defaults)
        use_submodules = [key for key, val in use_submodules.items()
                          if val == 'y']
    elif ask_submodules == 'n' and modules_def == {}:
        warnings.warn('You are fully importing every module and submodule'
                      'of packages %s' % packages)
        use_submodules = submodules
    else:
        use_submodules = [key for key, val in defaults.items() if val == 'y']
    return use_submodules


def list_all_submodules(package_name):
    subpackages, submodules = list_subs(package_name)
    for subp in subpackages:
        subpackages1, submodules1 = list_subs(subp)
        subpackages = subpackages1 + subpackages
        submodules = submodules1 + submodules
    return submodules


def list_subs(package_name):
    package = importlib.import_module(package_name)
    prefix = package.__name__ + "."
    submodules, subpackages = [], []
    for imp, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
        if ispkg:
            subpackages.append(modname)
        else:
            submodules.append(modname)
    return subpackages, submodules


def submodules_prompts(submodules, defaults):
    return {module: user_prompt('Include %s (y/n)? ' % module,
                                defaults[module],
                                inlist=['y', 'n']) for module in submodules}


def write_configs(config_file, cache_directory, submodules, exclusions):
    """
    Writes configurations to file
    """
    with open(config_file, 'w') as f:
        writer = csv.writer(f, delimiter='\n')
        writer.writerow(['Cache Directory:'])
        writer.writerow([cache_directory])
        writer.writerow([])
        writer.writerow([])
        writer.writerow(['Import Modules:'])
        [writer.writerow([module]) for module in submodules]
        writer.writerow([])
        writer.writerow([])
        writer.writerow(['Exclusions:'])
        [writer.writerow([excl]) for excl in exclusions]
