'''
Created on May 17, 2019

@author: Tim Kreuzer
'''

def get_token(path):
    with open(path, 'r') as f:
        token = f.read().rstrip()
    return token
