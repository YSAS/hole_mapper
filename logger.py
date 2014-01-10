import logging
import os

_configured=False

def setup_logging(name, logdir='', scrnlog=True, txtlog=False,
                  loglevel=logging.DEBUG):
    

    
    log = logging.getLogger(name)
    log.setLevel(loglevel)
    
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s :: %(message)s")
    
    if txtlog:
        logdir = os.path.abspath(logdir)
    
        if not os.path.exists(logdir):
            os.mkdir(logdir)
        txt_handler = RotatingFileHandler(
                                          os.path.join(logdir, name+".log"),
                                          backupCount=5)
        txt_handler.doRollover()
        txt_handler.setFormatter(log_formatter)
        log.addHandler(txt_handler)
        log.info("Logger initialised.")
    
    if scrnlog:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        log.addHandler(console_handler)


def getLogger(name):
    global _configured
    if not _configured:
        setup_logging(name)
        _configured=True
    return logging.getLogger(name)