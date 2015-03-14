import logging
import addict
import requests
import json
import os
from .. import config
RESULTS = { 'getUrl': {} }

from .insight import *
    
def _recordOutput(func):
    def call(*args, **kwargs):
        res = func(*args, **kwargs)
        if args: 
            RESULTS[func.__name__][".".join(args)] = res
        else: 
            RESULTS[func.__name__] = res
        return res
    return call

def _restoreOutput(func): 
    def call(*args, **kwargs):
        if args: 
            res = RESULTS[func.__name__][".".join(args)]
        else: 
            res = RESULTS[func.__name__]
        return res
    return call

def _wrapUrlGet(module, wrapper): 
    module.__dict__['getUrl'] = wrapper(getUrl) 
            
def _writeRecorderToFile(filename=None, path=None): 
    if not filename: 
        filename = "dummy_recorder.json"
    with open(os.path.join(path or config.DATA_DIR, filename), 'w') as wfile:
        print(RESULTS) 
        json.dump(RESULTS, wfile)

def _restoreOutputFromFile(filename=None, path=None): 
    global RESULTS
    if not filename: 
        filename = "dummy_recorder.json"
    with open(os.path.join(path or config.DATA_DIR, filename), 'r') as wfile:
        RESULTS = json.load(wfile)
    
