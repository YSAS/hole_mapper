import os.path

ROOT='./plates/'

def PLATE_DIRECTORY():
    return os.path.join(ROOT,'plates')+os.sep

def CONFIGDEF_DIRECTORY():
    return os.path.join(ROOT,'configs')+os.sep

def SETUP_DIRECTORY():
    return os.path.join(ROOT,'setups')+os.sep

def DEAD_FIBER_FILE():
    return os.path.join(CONFIGDEF_DIRECTORY(),'deadfibers.txt')

def OUTPUT_DIR():
    return os.path.join(ROOT,'output')+os.sep

def FIBERMAP_DIRECTORY():
    return OUTPUT_DIR()