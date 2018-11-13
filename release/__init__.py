import glob
import importlib
import os
import shutil
import sys
from os.path import join, isfile, dirname, relpath, isdir
from distutils.version import StrictVersion


COMPONENT_NAMES = {
    0: ['major'],
    1: ['minor'],
    2: ['patch', 'bugfix']
}

def get_component_ind(component_name):
    for k, v in COMPONENT_NAMES.items():
        if component_name.lower() in v:
            return k
    return None


def get_version(pkg):
    if not pkg:
        pkg = _find_package(pkg)
    return _get_cur_version(pkg)


def increment_version(arg='patch', pkg=None):
    if get_component_ind(arg) is not None:  # one of version component names
        cur_version = get_version(pkg)
        if cur_version is None:
            new_version = StrictVersion('0.0')
            err(f'Initialising with version {new_version}')
        else:
            components = list(cur_version.version)
            component_ind = get_component_ind(arg)
            err(f'Incrementing {arg} component {components[component_ind]}->{components[component_ind] + 1}')
            components[component_ind] = str(int(components[component_ind]) + 1)
            for lower_component_ind in range(component_ind + 1, len(components)):
                components[lower_component_ind] = 0

            cur_version.version = components
            cur_version.prerelease = None
            new_version = cur_version

    else:
        new_version = StrictVersion(arg)

    pkg = _find_package(pkg)
    version_py = join(pkg, '_version.py')
    git_rev = get_git_revision()
    with open(version_py, 'w') as f:
        f.write((
            f'# Do not edit this file, pipeline versioning is governed by git tags\n' +
            f'__version__ = \'{new_version}\'\n' +
            f'__git_revision__ = \'{git_rev}\'') + '\n')

    err(f'New version: {new_version}, written to {version_py}')
    return version_py, new_version


def clean_package(package_name, dirpath='.'):
    print('Cleaning up binary, build and dist for ' + package_name + ' in ' + dirpath + '...')
    if isdir(join(dirpath, 'build')):
        shutil.rmtree(join(dirpath, 'build'))
    if isdir(join(dirpath, 'dist')):
        shutil.rmtree(join(dirpath, 'dist'))
    if isdir(join(dirpath, package_name + '.egg-info')):
        shutil.rmtree(join(dirpath, package_name + '.egg-info'))
    print('Done.')


def get_reqs():
    try:  # for pip >= 10
        from pip._internal.req import parse_requirements
    except ImportError:  # for pip <= 9.0.3
        from pip.req import parse_requirements

    try:
        install_reqs = parse_requirements('requirements.txt', session=False)
    except TypeError:
        install_reqs = parse_requirements('requirements.txt')
    reqs = [str(ir.req) for ir in install_reqs if ir.req]
    return reqs


def find_package_files(dirpath, package, skip_exts=None):
    paths = []
    for (path, dirs, fnames) in os.walk(join(package, dirpath)):
        for fname in fnames:
            if skip_exts and any(fname.endswith(ext) for ext in skip_exts):
                continue
            fpath = join(path, fname)
            paths.append(relpath(fpath, package))
    return paths


def get_git_revision():
    try:
        import subprocess
        git_revision = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).rstrip()
    except:
        git_revision = ''
        pass
    if isinstance(git_revision, bytes):
        git_revision = git_revision.decode()
    return git_revision


def _get_cur_version(pkg):
    """ Tries to find _version.py or VERSION.txt with a value for a current version. On failure, returns None.
    """
    version_py = join(pkg, '_version.py')
    if isfile(version_py):
        cur_version = StrictVersion(importlib.import_module(f'{pkg}._version').__version__)
        err(f'Current version, read from {version_py}: {cur_version}')
    else:
        version_txt = 'VERSION.txt'
        if isfile(version_txt):
            cur_version = StrictVersion(open(version_txt).read().strip())
            err(f'Current version, read from {version_txt}: {cur_version}')
        else:
            cur_version = None
    return cur_version


def _find_package(pkg=None):
    found_verpy = glob.glob(f'{pkg or "*"}/_version.py')
    if len(found_verpy) > 1:
        err(f'Found multiple packages with _version.py: {found_verpy}. Please leave only one, it should be the main '
            f'package of your tool that you want to version.')
        sys.exit(1)
    elif len(found_verpy) == 1:
        pkg = dirname(found_verpy[0])
        err(f'Found package with _version.py file: {pkg}')
    else:
        pkg = None
        try:
            import setuptools
            pkgs = setuptools.find_packages()
            if len(pkgs) > 1:
                pkg = input(f'Multiple packages found: {pkgs}. Please specify the main package to version. '
                            f'It will create _version.py file in it and use it to keep track of the version:')
            elif len(pkgs) == 1:
                pkg = pkgs[0]
                err(f'Inititalising _version.py in package {pkg}')
        except:
            pass
        if pkg is None:
            pkg = input(f'Could not find any packages to version. Please, specify folder to inititate _version.py:')
    return pkg


def err(msg=''):
    sys.stderr.write(msg + '\n')
