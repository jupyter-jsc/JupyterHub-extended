'''
Created on May 10, 2019

@author: kreuzer
'''
import json
import uuid
import base64
import time
import requests
import jwt

from contextlib import closing

from jupyterhub.orm import User
from jupyterhub.utils import url_path_join
from jupyterhub.apihandlers.base import APIHandler

class J4J_APIUXHandler(APIHandler):
    async def post(self, username, server_name=''):  # @UnusedVariable
        uuidcode = uuid.uuid4().hex
        self.log.debug("uuidcode={} - UX Handler for username={} servername={}".format(uuidcode, username, server_name))
        user = self.find_user(username)
        self.log.debug("uuidcode={} - UX Handler: Headers: {}".format(uuidcode, self.request.headers))
        self.log.debug("uuidcode={} - UX Handler: Body: {}".format(uuidcode, self.request.body.decode("utf8")))
        if not user:
            self.set_status(404)
            self.write("User with name {} not found".format(username))
            self.flush()
            return
        data = self.request.body.decode("utf8")
        header = self.request.headers
        auth = header.get('Authorization', None)
        if not auth:
            self.set_status(401)
            self.write("No Authorization Header found")
            self.flush()
            return
        kernelurl = data.get('href', '')
        ux_info = user.authenticator.unicore_infos
        system = ""
        cert_url = ""
        cert_path = ""
        cert = ""
        for isystem, infos in ux_info.items():
            if kernelurl.startswith(infos.get('link', '...')):
                system = isystem
                cert_url = url_path_join(infos.get('link'), 'certificate')
                cert_path = infos.get('certificate', False)
                break
        if system != "":
            with closing(requests.get(cert_url, headers={'accept: text/plain'}, verify=cert_path)) as r:
                cert = r.text.decode("utf8")
        self.log.debug("uuidcode={} - UX Handler: PubCert: {}".format(uuidcode, cert))
        #bearer = auth.split(' ')[1]
        #verifying_key = jwt.jwk_from_pem(cert)
        #instance = jwt.JWT()
        #message_received = instance.decode(compact_jws, verifying_key, do_time_check=True)
        self.set_status(204)
        return
        
#         if user:
#             self.set_header('Content-Type', 'text/plain')
#             self.set_status(201)
#             self.log.debug("UID={} - uuidcode={} - load accesstoken from database.".format(user.name, uuidcode))
#             db_user = user.db.query(User).filter(User.name == user.name).first()
#             if db_user:
#                 user.db.refresh(db_user)
#                 user.encrypted_auth_state = db_user.encrypted_auth_state
#             state = await user.get_auth_state()
#             token = { 'accesstoken': state.get('accesstoken'), 'refreshtoken': state.get('refreshtoken'), 'expire': state.get('expire') }
#             if self.request.headers.get('renew', 'False').lower() == 'true':
#                 if int(token.get('expire')) - time.time() < 480:
#                     try:
#                         self.log.debug("uuidcode={} - UID={} - Try to update accesstoken".format(uuidcode, user.name))
#                         with open(user.authenticator.unity_file, 'r') as f:
#                             unity = json.load(f)
#                         if state.get('login_handler') == 'jscldap':
#                             b64key = base64.b64encode(bytes('{}:{}'.format(unity[user.authenticator.jscldap_token_url]['client_id'], unity[user.authenticator.jscldap_token_url]['client_secret']), 'utf-8')).decode('utf-8')
#                             data = {'refresh_token': token.get('refreshtoken'),
#                                     'grant_type': 'refresh_token',
#                                     'scope': ' '.join(unity[user.authenticator.jscldap_token_url]['scope'])}
#                             url = user.authenticator.jscldap_token_url
#                             info_url = unity[user.authenticator.jscldap_token_url]['links']['tokeninfo']
#                         elif state.get('login_handler') == 'jscusername':
#                             b64key = base64.b64encode(bytes('{}:{}'.format(unity[user.authenticator.jscusername_token_url]['client_id'], unity[user.authenticator.jscusername_token_url]['client_secret']), 'utf-8')).decode('utf-8')
#                             data = {'refresh_token': token.get('refreshtoken'),
#                                     'grant_type': 'refresh_token',
#                                     'scope': ' '.join(unity[user.authenticator.jscusername_token_url]['scope'])}
#                             url = user.authenticator.jscusername_token_url
#                             info_url = unity[user.authenticator.jscusername_token_url]['links']['tokeninfo']
#                         accesstoken = token.get('accesstoken')
#                         expire = token.get('expire')
#                         headers = {'Authorization': 'Basic {}'.format(b64key),
#                                    'Accept': 'application/json'}
#                         with closing(requests.post(url, headers=headers, data=data, verify=False)) as r:
#                             if r.status_code == 200:
#                                 accesstoken = r.json().get('access_token')
#                             else:
#                                 self.log.warning("uuidcode={} - UID={} - Could not update accesstoken: {} {}".format(uuidcode, user.name, r.status_code, r.text))
#                         with closing(requests.get(info_url, headers={ 'Authorization': 'Bearer {}'.format(accesstoken) }, verify=False)) as r:
#                             if r.status_code == 200:
#                                 expire = r.json().get('exp')
#                             else:
#                                 self.log.warning("uuidcode={} - UID={} - Could not receive token information: {} {}".format(uuidcode, user.name, r.status_code, r.text))
#                         state['accesstoken'] = accesstoken
#                         state['expire'] = expire
#                         await user.save_auth_state(state)
#                         token['accesstoken'] = accesstoken
#                         token['expire'] = expire
#                     except:
#                         self.log.exception("uuidcode={} - UID={} - Could not update accesstoken".format(uuidcode, user.name))
#             if self.request.headers.get('accounts', 'False').lower() == 'true':
#                 token['oauth_user'] = state.get('oauth_user')
#             self.write(json.dumps(token))
#             self.flush()
#         else:
#             self.set_status(404)
#             self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
#             self.flush()
        return