'''
Created on May 10, 2019

@author: kreuzer
'''
import json
import uuid
import base64
import time
import requests
import os

from contextlib import closing

from jupyterhub.orm import APIToken, User
from jupyterhub.apihandlers.base import APIHandler

class J4J_APITokenHandler(APIHandler):
    async def get(self, username, server_name=''):  # @UnusedVariable
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("uuidcode={} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
        self.log.debug("uuidcode={} - GetToken for servername={}".format(uuidcode, server_name))
        user = None
        try:
            if 'Authorization' in self.request.headers.keys():
                s = self.request.headers.get('Authorization').split()
                found = APIToken.find(self.db, token=s[1])
                if found is not None:
                    user = self._user_from_orm(found.user)
        except:
            self.log.debug("uuidcode={} - Could not find user for this token: {}".format(uuidcode, self.request.headers.get('Authorization', '<no Authorization header>')))
        #if not user:
        #    user = self.find_user(username)
        if user:
            self.set_header('Content-Type', 'text/plain')
            self.set_status(201)
            self.log.debug("UID={} - uuidcode={} - load accesstoken from database.".format(user.name, uuidcode))
            db_user = user.db.query(User).filter(User.name == user.name).first()
            if db_user:
                user.db.refresh(db_user)
                user.encrypted_auth_state = db_user.encrypted_auth_state
            state = await user.get_auth_state()
            token = { 'accesstoken': state.get('accesstoken'), 'refreshtoken': state.get('refreshtoken'), 'expire': state.get('expire') }
            if self.request.headers.get('renew', 'False').lower() == 'true':
                if int(token.get('expire')) - time.time() < 480:
                    try:
                        self.log.debug("uuidcode={} - UID={} - Try to update accesstoken".format(uuidcode, user.name))
                        with open(user.authenticator.unity_file, 'r') as f:
                            unity = json.load(f)
                        if state.get('login_handler') == 'jscldap':
                            b64key = base64.b64encode(bytes('{}:{}'.format(unity[user.authenticator.jscldap_token_url]['client_id'], unity[user.authenticator.jscldap_token_url]['client_secret']), 'utf-8')).decode('utf-8')
                            data = {'refresh_token': token.get('refreshtoken'),
                                    'grant_type': 'refresh_token',
                                    'scope': ' '.join(unity[user.authenticator.jscldap_token_url]['scope'])}
                            url = user.authenticator.jscldap_token_url
                            info_url = unity[user.authenticator.jscldap_token_url]['links']['tokeninfo']
                        elif state.get('login_handler') == 'jscusername':
                            b64key = base64.b64encode(bytes('{}:{}'.format(unity[user.authenticator.jscusername_token_url]['client_id'], unity[user.authenticator.jscusername_token_url]['client_secret']), 'utf-8')).decode('utf-8')
                            data = {'refresh_token': token.get('refreshtoken'),
                                    'grant_type': 'refresh_token',
                                    'scope': ' '.join(unity[user.authenticator.jscusername_token_url]['scope'])}
                            url = user.authenticator.jscusername_token_url
                            info_url = unity[user.authenticator.jscusername_token_url]['links']['tokeninfo']
                        accesstoken = token.get('accesstoken')
                        expire = token.get('expire')
                        headers = {'Authorization': 'Basic {}'.format(b64key),
                                   'Accept': 'application/json'}
                        with closing(requests.post(url, headers=headers, data=data, verify=False)) as r:
                            if r.status_code == 200:
                                accesstoken = r.json().get('access_token')
                            else:
                                self.log.warning("uuidcode={} - UID={} - Could not update accesstoken: {} {}".format(uuidcode, user.name, r.status_code, r.text))
                        with closing(requests.get(info_url, headers={ 'Authorization': 'Bearer {}'.format(accesstoken) }, verify=False)) as r:
                            if r.status_code == 200:
                                expire = r.json().get('exp')
                            else:
                                self.log.warning("uuidcode={} - UID={} - Could not receive token information: {} {}".format(uuidcode, user.name, r.status_code, r.text))
                        state['accesstoken'] = accesstoken
                        state['expire'] = expire
                        await user.save_auth_state(state)
                        token['accesstoken'] = accesstoken
                        token['expire'] = expire
                    except:
                        self.log.exception("uuidcode={} - UID={} - Could not update accesstoken".format(uuidcode, user.name))
            if self.request.headers.get('accounts', 'False').lower() == 'true':
                token['oauth_user'] = state.get('oauth_user')
            self.write(json.dumps(token))
            self.flush()
        else:
            self.set_status(404)
            self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
            self.flush()
        return

    async def post(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        self.log.debug("uuidcode={} - PostToken for servername={}".format(uuidcode, server_name))
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("uuidcode={} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
        data = self.request.body.decode("utf8")
        self.set_header('Content-Type', 'text/plain')
        if not data:
            self.set_status(400)
            self.write("Please send the token in the body as json: { \"accesstoken\": \"...\", \"expire\": \"...\" }")
            self.flush()
            return
        user = None
        if 'Authorization' in self.request.headers.keys():
            s = self.request.headers.get('Authorization').split()
            found = APIToken.find(self.db, token=s[1])
            if found is not None:
                user = self._user_from_orm(found.user)
        if not user:
            user = self.find_user(username)
        if user:
            data_json = json.loads(data)
            try:
                self.log.debug("uuidcode={} - UID={} - update accesstoken in database.".format(uuidcode, user.name))
                db_user = user.db.query(User).filter(User.name == user.name).first()
                if db_user:
                    user.db.refresh(db_user)
                    user.encrypted_auth_state = db_user.encrypted_auth_state
                state = await user.get_auth_state()
                state['accesstoken'] = data_json['accesstoken']
                state['expire'] = data_json['expire']
                await user.save_auth_state(state)
            except KeyError as e:
                self.set_status(400)
                self.write("Key {} missing".format(str(e)))
                self.flush()
                return
            self.set_header('Content-Type', 'text/plain')
            self.set_status(201)
        else:
            self.set_status(404)
            self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
            self.flush()
        return
