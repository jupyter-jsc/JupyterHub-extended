'''
Created on May 17, 2019

@author: Tim Kreuzer
'''

from contextlib import closing
import requests

def j4j_orchestrator_request(uuidcode, logger, method, method_args):
    logger.debug("uuidcode={} - J4J_Orchestrator_Request {}".format(uuidcode, method))
    if method == "POST":
        with closing(requests.post(method_args.get('url'),
                                   headers = method_args.get('headers', {}),
                                   data = method_args.get('data', '{}'),
                                   verify = method_args.get('certificate', False), timeout=3)) as r:
            return r.text, r.status_code, r.headers
    if method == "GET":
        with closing(requests.get(method_args.get('url'),
                                  headers = method_args.get('headers', {}),
                                  verify = method_args.get('certificate', False), timeout=3)) as r:
            return r.text, r.status_code, r.headers
    if method == "DELETE":
        with closing(requests.delete(method_args.get('url'),
                                     headers = method_args.get('headers', {}),
                                     json = {},
                                     verify = method_args.get('certificate', False), timeout=3)) as r:
            return r.text, r.status_code, r.headers
