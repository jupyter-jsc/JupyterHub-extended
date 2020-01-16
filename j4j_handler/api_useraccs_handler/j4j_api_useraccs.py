'''
Created on May 10, 2019

@author: kreuzer
'''

import uuid
import json
import base64
import time
import requests
import os

from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.orm import APIToken, User
from .utils import fit_partition

class J4J_APIUserAccsHandler(APIHandler):
    async def get(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        self.log.info("{} - Get UserAccs Status for user: {}".format(uuidcode, username))
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("{} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return

        user = self.find_user(username)
        if user:
            self.set_header('Content-Type', 'text/plain')
            self.set_status(200)
            self.log.debug("{} - {} - load useraccs status from database.".format(user.name, uuidcode))
            db_user = user.db.query(User).filter(User.name == user.name).first()
            if db_user:
                user.db.refresh(db_user)
                user.encrypted_auth_state = db_user.encrypted_auth_state
            state = await user.get_auth_state()
            complete = state.get('useraccs_complete')
            self.write(complete)
            self.flush()
        else:
            self.set_status(404)
            self.flush()
        return
    


    async def post(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        self.log.info("{} - Post useraccs for user: {}".format(uuidcode, username))
        self.log.info("{} - Host: {}".format(uuidcode, self.request.get("Host")))
        self.log.info("{} - Referer: {}".format(uuidcode, self.request.get("Referer")))
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("{} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
        data = self.request.body.decode("utf8")
        self.set_header('Content-Type', 'text/plain')
        if not data:
            self.set_status(400)
            self.write("Please send the token in the body as json: { \"accesstoken\": \"...\", \"expire\": \"...\" }")
            self.flush()
            return
        user = self.find_user(username)
        if user:
            try:
                data_json = json.loads(data)
                if not data_json.get('useraccs', None):
                    self.set_status(400)
                    self.log.debug("{} - No key useraccs in data: {}".format(uuidcode, data))
                    return
                db_user = user.db.query(User).filter(User.name == user.name).first()
                if db_user:
                    user.db.refresh(db_user)
                    user.encrypted_auth_state = db_user.encrypted_auth_state
                state = await user.get_auth_state()
                new_accs = fit_partition(data_json.get('useraccs'), user.authenticator.resources)
                for machine in new_accs.keys():
                    new_accs[machine]["!!DISCLAIMER!!"] = {}
                state['user_dic'].update(new_accs)
                state['useraccs_complete'] = True
                await user.save_auth_state(state)
                self.set_header('Content-Type', 'text/plain')
                self.set_status(204)
                return
            except:
                self.set_status(500)
                self.log.exception("{} - Could not update useraccs for user {}".format(uuidcode, username))
                return
        else:
            self.set_status(404)
            self.flush()
        return
