from __future__ import print_function
import setuptools, sys
import os
from setuptools.command.install import install
from setuptools.command.develop import develop
import subprocess
import platform
#pip install -e git+http://github.com/ysas/hole_mapper.git@main#egg=hole_mapper --user


def get_virtualenv_path():
    """Used to work out path to install compiled binaries to."""
    if hasattr(sys, 'real_prefix'):
        return sys.prefix
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        return sys.prefix
    if 'conda' in sys.prefix:
        return sys.prefix
    return None


def compile_and_install_software():
    """Used the subprocess module to compile/install the fortran software."""
    
    src_path = './hole_mapper/f90/'

    #If the fortran changes then first execute
    #   f2py m2fsholesxy.f90 -m m2fsholesxy -h m2fsholesxy.pyf only: m2fsholesxy :
    # replace 'integer, optional,intent(hide),depend(rastars) :: nmax=len(rastars)+100'
    # with 'integer, optional,intent(hide),depend(rastars) :: nmax=len(rastars)*4'
    #and add that to the repository
    
    venv = get_virtualenv_path()
    cmd = 'f2py -c m2fsholesxy.pyf *.f90 -m m2fsholesxy'
    if venv:
        cmd += ' --prefix=' + os.path.abspath(venv)
    
    try:
        subprocess.check_call(cmd, cwd=src_path, shell=True)
    except Exception as e:
        print(str(e))
        raise e

class CustomInstall(install, object):
    """Custom handler for the 'install' command."""
    def run(self):
        compile_and_install_software()
        super(CustomInstall,self).run()

class CustomDevelop(develop, object):
    """Custom handler for the 'install' command."""
    def run(self):
        compile_and_install_software()
        super(CustomDevelop,self).run()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
                 name="hole_mapper",
                 version="1.0",
                 author="Jeb Bailey",
                 author_email="bailey@ucsb.edu",
                 description="M2FS Plate Preparation Software",
                 long_description=long_description,
                 long_description_content_type="text/markdown",
                 url="https://github.com/ysas/hole_mapper",
                 packages=setuptools.find_packages(),
                 scripts=['hole_mapper/plate_driller.py',
                          'hole_mapper/fiber_assigner.py'],
                 classifiers=("Programming Language :: Python :: 2",
                              "License :: OSI Approved :: MIT License",
                              "Operating System :: POSIX",
                              "Development Status :: 1 - Planning",
                              "Intended Audience :: Science/Research"),
                 cmdclass={'install': CustomInstall,'develop': CustomDevelop}
                 )



