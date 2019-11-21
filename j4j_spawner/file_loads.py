'''
Created on May 17, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

def get_token(path):
    with open(path, 'r') as f:
        token = f.read().rstrip()
    return token
