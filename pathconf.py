import os.path

ROOT='./'

def PLATE_DIRECTORY():
    return os.path.join(ROOT,'plates')+os.sep

def CONFIGDEF_DIRECTORY():
    return os.path.join(ROOT,'configs')+os.sep

def SETUP_DIRECTORY():
    return os.path.join(ROOT,'setups')+os.sep

def DEAD_FIBER_FILE():
    return os.path.join(CONFIGDEF_DIRECTORY(),'deadfibers.txt')