import os.path
import tkMessageBox
import tkFileDialog

ROOT='./plates/'
run_params_dir=None
m2fs_params_dir=None
setups_dir=None
output_dir=None

def PLATE_DIRECTORY():
    if run_params_dir: #User provided directory
        return os.path.join(run_params_dir)+os.sep
    else: #Default if no user provided directory
        return os.path.join(ROOT,'Run_Params')+os.sep

def CONFIGDEF_DIRECTORY():
    if m2fs_params_dir: #User provided directory
        return os.path.join(m2fs_params_dir)+os.sep
    else: #Default if no user provided directory
        return os.path.join(ROOT,'M2FS_Params')+os.sep


def SETUP_DIRECTORY():
    if setups_dir: #User provided directory
        return os.path.join(setups_dir)+os.sep
    else: #Default if no user provided directory
        return os.path.join(ROOT,'setups')+os.sep

def DEAD_FIBER_FILE():
    return os.path.join(PLATE_DIRECTORY(),'deadfibers.txt')

def OUTPUT_DIR():
    if output_dir: #User provided directory
        return os.path.join(output_dir)+os.sep
    elif os.path.isdir(os.path.join(ROOT,'output')+os.sep): #Default if no user provided directory
        return os.path.join(ROOT,'output')+os.sep
    else:
        return os.path.join(ROOT)+os.sep

def FIBERMAP_DIRECTORY():
    return OUTPUT_DIR()
