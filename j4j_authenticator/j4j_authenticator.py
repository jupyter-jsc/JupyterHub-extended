import os
import uuid
import base64
import urllib
import json
import requests
import re

from contextlib import closing
from subprocess import STDOUT, check_output, CalledProcessError
from traitlets import Unicode, Bool, List
from jupyterhub import orm
from jupyterhub.objects import Server
from tornado import web
from tornado.auth import OAuth2Mixin
from tornado.httpclient import HTTPRequest, AsyncHTTPClient
from tornado.httputil import url_concat
from oauthenticator.oauth2 import OAuthLoginHandler, OAuthCallbackHandler
from oauthenticator.generic import GenericOAuthenticator

from .j4j_logout import J4J_LogoutHandler
from .utils import get_user_dic 
from j4j_authenticator import utils
import time

class HDFAAICallbackHandler(OAuthCallbackHandler):
    pass

class HDFAAIEnvMixin(OAuth2Mixin):
    _OAUTH_ACCESS_TOKEN_URL = os.environ.get('HDFAAI_TOKEN_URL', 'https://unity.helmholtz-data-federation.de/oauth2/token')
    _OAUTH_AUTHORIZE_URL = os.environ.get('HDFAAI_AUTHORIZE_URL', 'https://unity.helmholtz-data-federation.de/oauth2-as/oauth2-authz')

class HDFAAILoginHandler(OAuthLoginHandler, HDFAAIEnvMixin):
    def get(self):
        with open(self.authenticator.unity_file, 'r') as f:
            unity = json.load(f)
        redirect_uri = self.authenticator.get_callback_url(None, "HDFAAI")
        self.log.info('OAuth redirect: %r', redirect_uri)
        state = self.get_state()
        self.set_state_cookie(state)
        self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=unity[self.authenticator.hdfaai_token_url]['client_id'],
            scope=unity[self.authenticator.hdfaai_authorize_url]['scope'],
            extra_params={'state': state},
            response_type='code')


class JSCLDAPCallbackHandler(OAuthCallbackHandler):
    pass

class JSCLDAPEnvMixin(OAuth2Mixin):
    _OAUTH_ACCESS_TOKEN_URL = os.environ.get('JSCLDAP_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token')
    _OAUTH_AUTHORIZE_URL = os.environ.get('JSCLDAP_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as/oauth2-authz')

class JSCLDAPLoginHandler(OAuthLoginHandler, JSCLDAPEnvMixin):
    def get(self):
        with open(self.authenticator.unity_file, 'r') as f:
            unity = json.load(f)
        redirect_uri = self.authenticator.get_callback_url(None, "JSCLDAP")
        self.log.debug('OAuth redirect: %r', redirect_uri)
        state = self.get_state()
        self.set_state_cookie(state)
        self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=unity[self.authenticator.jscldap_token_url]['client_id'],
            scope=unity[self.authenticator.jscldap_authorize_url]['scope'],
            extra_params={'state': state},
            response_type='code')

class JSCUsernameCallbackHandler(OAuthCallbackHandler):
    pass

class JSCUsernameEnvMixin(OAuth2Mixin):
    _OAUTH_ACCESS_TOKEN_URL = os.environ.get('JSCUSERNAME_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token')
    _OAUTH_AUTHORIZE_URL = os.environ.get('JSCUSERNAME_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as-username/oauth2-authz')

class JSCUsernameLoginHandler(OAuthLoginHandler, JSCUsernameEnvMixin):
    def get(self):
        with open(self.authenticator.unity_file, 'r') as f:
            unity = json.load(f)
        redirect_uri = self.authenticator.get_callback_url(None, "JSCUsername")
        self.log.debug('OAuth redirect: %r', redirect_uri)
        state = self.get_state()
        self.set_state_cookie(state)
        self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=unity[self.authenticator.jscusername_token_url]['client_id'],
            scope=unity[self.authenticator.jscusername_authorize_url]['scope'],
            extra_params={'state': state},
            response_type='code')


class BaseAuthenticator(GenericOAuthenticator):
    login_service = Unicode(
        "Jupyter@JSC Authenticator",
        config=True
    )

    unity_file = Unicode(
        os.environ.get('UNITY_FILE', ''),
        config=True,
        help="Path to unity file with links and other stuff"
    )

    multiple_instances = Bool(
        os.environ.get('MULTIPLE_INSTANCES', 'false').lower() in {'true', '1'},
        config=True,
        help="Is this JupyterHub instance running with other instances behind the same proxy with the same database?"
    )

    hdfaai_restriction_path = Unicode(
        os.getenv('HDFAAI_RESTRICTION_PATH', '/etc/j4j/j4j_mount/j4j_hub/authenticators/hdfaai.json'),
        config=True,
        help="If username is in this list -> let him through."
    )

    hdfaai_callback_url = Unicode(
        os.getenv('HDFAAI_CALLBACK_URL', 'https://jupyter-jsc.fz-juelich.de/hub/hdfaai_callback'),
        config=True,
        help="""Callback URL to use.
        Typically `https://{host}/hub/oauth_callback`"""
    )

    hdfaai_token_url = Unicode(
        os.environ.get('HDFAAI_TOKEN_URL', 'https://unity.helmholtz-data-federation.de/oauth2/token'),
        config=True,
        help="Access token endpoint URL for HDFAAI"
    )

    hdfaai_authorize_url = Unicode(
        os.environ.get('HDFAAI_AUTHORIZE_URL', 'https://unity.helmholtz-data-federation.de/oauth2-as/oauth2-authz'),
        config=True,
        help="Authorize URL for HDFAAI Login"
    )

    jscldap_callback_url = Unicode(
        os.getenv('JSCLDAP_CALLBACK_URL', 'https://jupyter-jsc.fz-juelich.de/hub/jscldap_callback'),
        config=True,
        help="""Callback URL to use.
        Typically `https://{host}/hub/oauth_callback`"""
    )

    jscldap_token_url = Unicode(
        os.environ.get('JSCLDAP_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token'),
        config=True,
        help="Access token endpoint URL for JSCLdap"
    )

    jscldap_authorize_url = Unicode(
        os.environ.get('JSCLDAP_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as/oauth2-authz'),
        config=True,
        help="Authorize URL for JSCLdap Login"
    )

    jscusername_callback_url = Unicode(
        os.getenv('JSCUSERNAME_CALLBACK_URL', 'https://jupyter-jsc.fz-juelich.de/hub/jscusername_callback'),
        config=True,
        help="""Callback URL to use.
        Typically `https://{host}/hub/oauth_callback`"""
    )

    jscusername_token_url = Unicode(
        os.environ.get('JSCUSERNAME_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token'),
        config=True,
        help="Access token endpoint URL for JSCUsername"
    )

    jscusername_authorize_url = Unicode(
        os.environ.get('JSCUSERNAME_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as-username/oauth2-authz'),
        config=True,
        help="Authorize URL for JSCUsername Login"
    )

    hpc_infos_key = Unicode(
        os.environ.get('OAUTH2_HPC_INFOS_KEY', ''),
        config=True,
        help="Userdata hpc_infos key from returned json for USERDATA_URL"
    )

    hpc_infos_ssh_key = Unicode(
        config=True,
        help=''
    )

    hpc_infos_ssh_user = Unicode(
        config=True,
        help=''
    )

    hpc_infos_ssh_host = Unicode(
        config=True,
        help=''
    )

    hpc_infos_add_queues = List(
        config=True,
        help='',
        default_value=[]
    )

    j4j_urls_paths = Unicode(
        os.environ.get('OAUTH2_J4J_URLS_PATHS', ''),
        config=True,
        help="Path to the urls needed for j4j"
    )

    j4j_user_agent = Unicode(
        os.environ.get('OAUTH2_J4J_USER_AGENT', 'Jupyter@JSC'),
        config = True,
        help="User-Agent variable for communications"
    )

    resources = Unicode( # Used outside Authenticator
        os.environ.get('RESOURCES_PATH', ''),
        config = True,
        help = "Path to the filled_resources file"
    )

    unicore = Unicode( 
        os.environ.get('UNICORE_PATH', ''),
        config = True,
        help = "Path to the unicore.json file"
    )

    proxy_secret = Unicode( # Used outside Authenticator
        os.environ.get('PROXY_SECRET', ''),
        config = True,
        help = "Path to the configurable http proxy secret file"
    )

    orchestrator_token_path = Unicode( # Used outside Authenticator
        os.environ.get('ORCHESTRATOR_TOKEN_PATH', ''),
        config = True,
        help = "Path to the J4J_Orchestrator token file"
    )

    tunnel_token_path = Unicode( # Used outside Authenticator
        os.environ.get('TUNNEL_TOKEN_PATH', ''),
        config = True,
        help = "Path to the J4J_Tunnel token file"
    )

    reservation_path = Unicode(
        os.environ.get("RESERVATION_PATH", ""),
        config = True,
        help = "Path to all reservations"
    )
    
    enable_auth_state = Bool(
        os.environ.get('ENABLE_AUTH_STATE', False).lower() in {'true', '1'},
        config=True,
        help="""Enable persisting auth_state (if available).

        auth_state will be encrypted and stored in the Hub's database.
        This can include things like authentication tokens, etc.
        to be passed to Spawners as environment variables.

        Encrypting auth_state requires the cryptography package.

        Additionally, the JUPYTERHUB_CRYPT_KEY environment variable must
        contain one (or more, separated by ;) 32B encryption keys.
        These can be either base64 or hex-encoded.

        If encryption is unavailable, auth_state cannot be persisted.

        New in JupyterHub 0.8
        """,
    )
    
    _reservations = {}
    _reservation_next_update = 0
    
    def get_reservations(self):
        if len(self._reservations) > 0 and self._reservation_next_update - int(time.time()) > 0:
            return self._reservations
        else:
            try:
                tmp_dic = {}
                for system_reservation in os.listdir(self.reservation_path):
                    system_reservation_path = os.path.join(self.reservation_path, system_reservation)
                    system = system_reservation.split("_")[0]
                    tmp_dic[system] = system_reservation_path
                self._reservations = utils.reservations(tmp_dic)
                self._reservation_next_update = int(time.time()) + 300
                self.log.info("Updated Reservations: {}".format(self._reservations))
                return self._reservations
            except:
                self._reservations = {}
                return self._reservations
            

    login_handler = [JSCLDAPLoginHandler, JSCUsernameLoginHandler, HDFAAILoginHandler]
    logout_handler = J4J_LogoutHandler
    callback_handler = [JSCLDAPCallbackHandler, JSCUsernameCallbackHandler, HDFAAICallbackHandler]

    def get_handlers(self, app):
        return [
            (r'/jscldap_login', self.login_handler[0]),
            (r'/jscldap_callback', self.callback_handler[0]),
            (r'/jscusername_login', self.login_handler[1]),
            (r'/jscusername_callback', self.callback_handler[1]),
            (r'/hdfaai_login', self.login_handler[2]),
            (r'/hdfaai_callback', self.callback_handler[2]),
            (r'/logout', self.logout_handler)
        ]

    def get_callback_url(self, handler=None, authenticator_name=""):
        if authenticator_name == "JSCLDAP":
            return self.jscldap_callback_url
        elif authenticator_name == "JSCUsername":
            return self.jscusername_callback_url
        elif authenticator_name == "HDFAAI":
            return self.hdfaai_callback_url
        else:
            return "<unknown_callback_url>"

    def remove_secret(self, json_dict):
        if type(json_dict) != dict:
            return json_dict
        secret_dict = {}
        for key, value in json_dict.items():
            if type(value) == dict:
                secret_dict[key] = self.remove_secret(value)
            elif key.lower() in ["authorization", "accesstoken", "refreshtoken", "jhubtoken"]:
                secret_dict[key] = '<secret>'
            else:
                secret_dict[key] = value
        return secret_dict

    async def update_mem(self, user, caller):
        try:
            self.log.debug("{} - Update memory of spawner. Called by: {}".format(user.name, caller))
            with open(self.j4j_urls_paths, 'r') as f:
                j4j_paths = json.load(f)
            with open(j4j_paths.get('hub', {}).get('path_partitions', '<no_path_found>'), 'r') as f:
                resources_filled = json.load(f)
            db_user = user.db.query(orm.User).filter(orm.User.name == user.name).first()
            user.db.refresh(db_user)
            db_spawner_all = user.db.query(orm.Spawner).filter(orm.Spawner.user_id == db_user.id).all()
            user_state = await user.get_auth_state()
            if user_state:
                user_dic = user_state.get('user_dic', {})
            else:
                self.log.info("{} - Could not get auth_state for user {}".format(caller, user.name))
                return
            spawner = {}
            name_list = []
            for db_spawner in db_spawner_all:
                name_list.append(db_spawner.name)
                if db_spawner.name == '':
                    continue
                user.db.refresh(db_spawner)
                spawner[db_spawner.name] = {}
                #self.log.debug("{} - Check Spawner {}".format(user.name, db_spawner.name))
                if db_spawner.server_id:
                    #self.log.debug("{} - Spawner {} is active (has a server_id)".format(user.name, db_spawner.name))
                    spawner[db_spawner.name]['active'] = True
                    spawner[db_spawner.name]['server_id'] = db_spawner.server_id
                else:
                    #self.log.debug("{} - Spawner {} is not active (has no server_id)".format(user.name, db_spawner.name))
                    spawner[db_spawner.name]['active'] = False
                if db_spawner.user_options and 'system' in db_spawner.user_options.keys():
                    if db_spawner.user_options.get('system').upper() == 'DOCKER':
                        spawner[db_spawner.name]['spawnable'] = True
                    else:
                        if db_spawner.user_options.get('reservation', '') != '':
                            if self.get_reservations().get(db_spawner.user_options.get('system').upper(), {}).get(db_spawner.user_options.get('reservation'), {}).get('State', 'INACTIVE').upper() == "ACTIVE":
                                spawner[db_spawner.name]['spawnable'] = db_spawner.user_options.get('system').upper() in resources_filled.keys() and db_spawner.user_options.get('system').upper() in user_dic.keys()
                            else:
                                spawner[db_spawner.name]['spawnable'] = False
                        else:
                            spawner[db_spawner.name]['spawnable'] = db_spawner.user_options.get('system').upper() in resources_filled.keys() and db_spawner.user_options.get('system').upper() in user_dic.keys()
                else:
                    spawner[db_spawner.name]['spawnable'] = True
                spawner[db_spawner.name]['state'] = db_spawner.state
                #self.log.debug("{} - Spawner {} spawnable: {}".format(user.name, db_spawner.name, spawner[db_spawner.name]['spawnable']))
            to_pop_list = []
            for name in user.spawners.keys():
                if name not in name_list:
                    to_pop_list.append(name)
            for name in sorted(user.orm_user.orm_spawners.keys()):
                if name == '':
                    continue
                if name not in user.spawners.keys():
                    #self.log.debug("{} - Create wrapper for {}".format(user.name, name))
                    user.spawners[name] = user._new_spawner(name)
                # get wrapper if it exists (server may be active)
                user.spawners[name].load_state(spawner[name]['state'])
                # has the spawner_id changed? If so -> recreate in memory
                for db_spawner in db_spawner_all:
                    if db_spawner.name == name:
                        try:
                            unused_tmp = user.spawners[name].orm_spawner.id # If this throws an exception we have to replace the spawner in memory
                            #self.log.debug("{} - {} : Mem_spawner_id: {}".format(user.name, name, user.spawners[name].orm_spawner.id))
                        except:
                            #self.log.debug("{} - {}: It's not there anymore".format(user.name, name))
                            user.spawners.pop(name, None)
                            #self.log.debug("{} - {}: Add new one in memory".format(user.name, name))
                            user.spawners[name] = user._new_spawner(name)
                            user.spawners[name].spawnable = spawner[name]['spawnable']
                            user.orm_user.orm_spawners.get(name).spawnable = spawner[name]['spawnable']
                            self.spawnable_dic[user.name][name] = spawner[name]['spawnable']
                if user.spawners[name].active:
                    #self.log.debug("{} - Spawner {} is in memory and active".format(user.name, name))
                    if not spawner[name]['active']:
                        uuidcode = uuid.uuid4().hex
                        self.log.debug("{} - Spawner servername={} should not be active. Delete it: uuidcode={}".format(user.name, name, uuidcode))
                        try:
                            await user.spawners[name].cancel(uuidcode, True)
                        except:
                            self.log.warning("uuidcode={} - Could not cancel server. Try to stop it".format(uuidcode))
                            try:
                                await user.stop(name)
                            except:
                                self.log.warning("uuidcode={} - Could not stop server. Try to delete it".format(uuidcode))
                                try:
                                    del user.spawners[name]
                                except:
                                    self.log.warning("uuidcode={} - Could not delete from dict".format(uuidcode))
                    else:
                        #self.log.debug("{} - Spawner {} should be active. Check server_url and port".format(user.name, name))
                        db_server = user.db.query(orm.Server).filter(orm.Server.id == spawner[name]['server_id']).first()
                        user.db.refresh(db_server)
                        if db_server.base_url != user.spawners[name].server.base_url or db_server.port != user.spawners[name].server.port:
                            #self.log.debug("Bind_URLs from server {} are different between Database {} and memory {}. Trust the database and delete the own server".format(name, db_server, user.spawners[name].server))
                            old_server = user.db.query(orm.Server).filter(orm.Server.id == user.spawners[name].orm_spawner.server_id).first()
                            if old_server:
                                #self.log.debug("Delete old server {} from database".format(old_server))
                                user.db.expunge(old_server)
                            user.spawners[name].orm_spawner.server = None
                            user.spawners[name].server = Server(orm_server=db_server)
                else:
                    if spawner[name]['active']:
                        #self.log.debug("{} - Spawner {} should be active. So create a Server in memory for it".format(user.name, name))
                        for db_spawner in db_spawner_all:
                            if db_spawner.name == name:
                                user.spawners[name].orm_spawner = db_spawner
                        db_server = user.db.query(orm.Server).filter(orm.Server.id == spawner[name]['server_id']).first()
                        user.db.refresh(db_server)
                        user.spawners[name].orm_spawner.server = None
                        user.spawners[name].server = Server(orm_server=db_server)
                        #self.log.debug("{} - Spawner {} active is now: {}".format(user.name, name, user.spawners[name].active))
                    #else:
                    #    self.log.debug("{} - Spawner {} should not be active. Everything's fine".format(user.name, name))
                    if self.spawnable_dic.get(user.name) == None:
                        self.spawnable_dic[user.name] = {}
                    user.spawners[name].spawnable = spawner[name]['spawnable']
                    user.orm_user.orm_spawners.get(name).spawnable = spawner[name]['spawnable']
                    self.spawnable_dic[user.name][name] = spawner[name]['spawnable']
            if len(to_pop_list) > 0:
                for name in to_pop_list:
                    #self.log.debug("{} - Remove {} from memory".format(user.name, name))
                    user.spawners.pop(name, None)
            #if len(to_add_list) > 0:
            #    for name in to_add_list:
            #        self.log.debug("{} - Add {} to memory".format(user.name, name))
            #        user.spawners[name] = user._new_spawner(name)
            #        user.spawners[name].spawnable = spawner[name]['spawnable']
            #        user.orm_user.orm_spawners.get(name).spawnable = spawner[name]['spawnable']
            #        self.spawnable_dic[user.name][name] = spawner[name]['spawnable']
            for dirty_obj in user.db.dirty:
                self.log.debug("{} - Refresh {}".format(user.name, dirty_obj))
                self.db.refresh(dirty_obj)
        except:
            self.log.exception("{} - Could not update memory".format(user.name))

    spawnable_dic = {}
    def spawnable(self, user_name, server_name):
        try:
            if user_name in self.spawnable_dic.keys() and server_name in self.spawnable_dic[user_name].keys():
                return self.spawnable_dic[user_name][server_name]
            else:
                return True
        except:
            return True

    async def authenticate(self, handler, data=None):
        uuidcode = uuid.uuid4().hex
        if (handler.__class__.__name__ == "JSCLDAPCallbackHandler"):
            self.log.debug("uuidcode={} - Call JSCLDAP_authenticate".format(uuidcode))
            return await self.jscldap_authenticate(handler, uuidcode, data)
        elif (handler.__class__.__name__ == "JSCUsernameCallbackHandler"):
            self.log.debug("uuidcode={} - Call JSCUsername_authenticate".format(uuidcode))
            return await self.jscusername_authenticate(handler, uuidcode, data)
        elif (handler.__class__.__name__ == "HDFAAICallbackHandler"):
            self.log.debug("uuidcode={} - Call HDFAAI_authenticate".format(uuidcode))
            return await self.hdfaai_authenticate(handler, uuidcode, data)
        else:
            self.log.warning("uuidcode={} - Unknown CallbackHandler: {}".format(uuidcode, handler.__class__))
            return "Username"

    async def hdfaai_authenticate(self, handler, uuidcode, data=None):
        with open(self.unity_file, 'r') as f:
            unity = json.load(f)
        code = handler.get_argument("code")
        http_client = AsyncHTTPClient()
        params = dict(
            redirect_uri=self.get_callback_url(None, "HDFAAI"),
            code=code,
            grant_type='authorization_code'
        )
        params.update(self.extra_params)

        if self.hdfaai_token_url:
            url = self.hdfaai_token_url
        else:
            raise ValueError("{} - Please set the HDFAAI_TOKEN_URL environment variable".format(uuidcode))

        b64key = base64.b64encode(
            bytes(
                "{}:{}".format(unity[self.hdfaai_token_url]['client_id'], unity[self.hdfaai_token_url]['client_secret']),
                "utf8"
            )
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": self.j4j_user_agent,
            "Authorization": "Basic {}".format(b64key.decode("utf8"))
        }
        req = HTTPRequest(url,
                          method="POST",
                          headers=headers,
                          validate_cert=self.tls_verify,
                          body=urllib.parse.urlencode(params)
                          )

        resp = await http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))
        self.log.debug("uuidcode={} , First response: {}".format(uuidcode, resp_json))

        accesstoken = resp_json.get('access_token', None)
        refreshtoken = resp_json.get('refresh_token', None)
        token_type = resp_json.get('token_type', None)
        scope = resp_json.get('scope', '')
        if (isinstance(scope, str)):
            scope = scope.split(' ')

        # Determine who the logged in user is
        headers = {
            "Accept": "application/json",
            "User-Agent": self.j4j_user_agent,
            "Authorization": "{} {}".format(token_type, accesstoken)
        }
        url = url_concat(unity[self.hdfaai_token_url]['links']['userinfo'], unity[self.hdfaai_token_url].get('userdata_params', {}))

        req = HTTPRequest(url,
                          method=unity[self.hdfaai_token_url].get('userdata_method', 'GET'),
                          headers=headers,
                          validate_cert=self.tls_verify)
        resp = await http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))
        self.log.debug("uuidcode={} , Second response: {}".format(uuidcode, resp_json))

        username_key = unity[self.hdfaai_authorize_url]['username_key']

        if not resp_json.get(username_key):
            self.log.error("uuidcode={} - OAuth user contains no key {}: {}".format(uuidcode, username_key, self.remove_secret(resp_json)))
            return

        req_exp = HTTPRequest(unity[self.hdfaai_token_url]['links']['tokeninfo'],
                              method=unity[self.hdfaai_token_url].get('tokeninfo_method', 'GET'),
                              headers=headers,
                              validate_cert=self.tls_verify)
        resp_exp = await http_client.fetch(req_exp)
        resp_json_exp = json.loads(resp_exp.body.decode('utf8', 'replace'))
        self.log.debug("uuidcode={} , Third response: {}".format(uuidcode, resp_json_exp))

        tokeninfo_exp_key = unity[self.hdfaai_token_url].get('tokeninfo_exp_key', 'exp')
        if not resp_json_exp.get(tokeninfo_exp_key):
            self.log.error("uuidcode={} - Tokeninfo contains no key {}: {}".format(uuidcode, tokeninfo_exp_key, self.remove_secret(resp_json_exp)))
            return

        expire = str(resp_json_exp.get(tokeninfo_exp_key))
        username = resp_json.get(username_key)
        username = self.normalize_username(username)
        with open(self.hdfaai_restriction_path, 'r') as f:
            hdfaai_restriction = json.load(f)
        if username not in hdfaai_restriction:
            raise web.HTTPError(403, "You're not allowed to use this service. Please contact support.")
        self.log.info("uuidcode={}, action=login, aai=hdfaai, username={}".format(uuidcode, username))

        return {
                'name': username,
                'auth_state': {
                               'accesstoken': accesstoken,
                               'refreshtoken': refreshtoken,
                               'expire': expire,
                               'oauth_user': resp_json,
                               'user_dic': {},
                               'useraccs_complete': True,
                               'scope': scope,
                               'login_handler': 'hdfaai',
                               'errormsg': ''
                               }
                }


    async def jscldap_authenticate(self, handler, uuidcode, data=None):
        with open(self.unity_file, 'r') as f:
            unity = json.load(f)
        code = handler.get_argument("code")
        http_client = AsyncHTTPClient()
        params = dict(
            redirect_uri=self.get_callback_url(None, "JSCLDAP"),
            code=code,
            grant_type='authorization_code'
        )
        params.update(self.extra_params)

        if self.jscldap_token_url:
            url = self.jscldap_token_url
        else:
            raise ValueError("uuidcode={} - Please set the JSCLDAP_TOKEN_URL environment variable".format(uuidcode))

        b64key = base64.b64encode(
            bytes(
                "{}:{}".format(unity[self.jscldap_token_url]['client_id'], unity[self.jscldap_token_url]['client_secret']),
                "utf8"
            )
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": self.j4j_user_agent,
            "Authorization": "Basic {}".format(b64key.decode("utf8"))
        }
        req = HTTPRequest(url,
                          method="POST",
                          headers=headers,
                          validate_cert=self.tls_verify,
                          body=urllib.parse.urlencode(params)
                          )

        resp = await http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))

        accesstoken = resp_json.get('access_token', None)
        refreshtoken = resp_json.get('refresh_token', None)
        token_type = resp_json.get('token_type', None)
        scope = resp_json.get('scope', '')
        if (isinstance(scope, str)):
            scope = scope.split(' ')

        # Determine who the logged in user is
        headers = {
            "Accept": "application/json",
            "User-Agent": self.j4j_user_agent,
            "Authorization": "{} {}".format(token_type, accesstoken)
        }
        url = url_concat(unity[self.jscldap_token_url]['links']['userinfo'], unity[self.jscldap_token_url].get('userdata_params', {}))

        req = HTTPRequest(url,
                          method=unity[self.jscldap_token_url].get('userdata_method', 'GET'),
                          headers=headers,
                          validate_cert=self.tls_verify)
        resp = await http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))

        username_key = unity[self.jscldap_authorize_url]['username_key']

        if not resp_json.get(username_key):
            self.log.error("uuidcode={} - OAuth user contains no key {}: {}".format(uuidcode, username_key, self.remove_secret(resp_json)))
            return

        req_exp = HTTPRequest(unity[self.jscldap_token_url]['links']['tokeninfo'],
                              method=unity[self.jscldap_token_url].get('tokeninfo_method', 'GET'),
                              headers=headers,
                              validate_cert=self.tls_verify)
        resp_exp = await http_client.fetch(req_exp)
        resp_json_exp = json.loads(resp_exp.body.decode('utf8', 'replace'))

        tokeninfo_exp_key = unity[self.jscldap_token_url].get('tokeninfo_exp_key', 'exp')
        if not resp_json_exp.get(tokeninfo_exp_key):
            self.log.error("uuidcode={} - Tokeninfo contains no key {}: {}".format(uuidcode, tokeninfo_exp_key, self.remove_secret(resp_json_exp)))
            return

        expire = str(resp_json_exp.get(tokeninfo_exp_key))
        username = resp_json.get(username_key).split('=')[1]
        username = self.normalize_username(username)
        self.log.info("uuidcode={}, action=login, aai=jscldap, username={}".format(uuidcode, username))
        self.log.debug("uuidcode={}, action=revoke, username={}".format(uuidcode, username))
        try:
            with open(self.j4j_urls_paths, 'r') as f:
                j4j_paths = json.load(f)
            with open(j4j_paths.get('token', {}).get('orchestrator', '<no_token_found>'), 'r') as f:
                orchestrator_token = f.read().rstrip()
            json_dic = { 'accesstoken': accesstoken,
                         'refreshtoken': refreshtoken }
            header = {'Intern-Authorization': orchestrator_token,
                      'uuidcode': uuidcode,
                      'stopall': 'false',
                      'username': username,
                      'expire': expire,
                      'tokenurl': self.jscldap_token_url,
                      'authorizeurl': self.jscldap_token_url,
                      'allbutthese': 'true' }
            url = j4j_paths.get('orchestrator', {}).get('url_revoke', '<no_url_found>')
            with closing(requests.post(url,
                                      headers=header,
                                      json=json_dic,
                                      verify=False)) as r:
                if r.status_code != 202:
                    self.log.warning("uuidcode={} - Failed J4J_Orchestrator communication: {} {}".format(uuidcode, r.text, r.status_code))
        except:
            self.log.exception("uuidcode={} - Could not revoke old tokens for {}".format(uuidcode, username))

        # collect hpc infos with the known ways
        hpc_infos = resp_json.get(self.hpc_infos_key, '')
        self.log.debug("uuidcode={} - Unity sent these hpc_infos: {}".format(uuidcode, hpc_infos))

        # If it's empty we assume that it's a new registered user. So we collect the information via ssh to UNICORE.
        # Since the information from Unity and ssh are identical, it makes no sense to do it if len(hpc_infos) != 0
        if len(hpc_infos) == 0:
            try:
                self.log.debug("uuidcode={} - Try to get HPC_Infos via ssh".format(uuidcode))
                hpc_infos = self.get_hpc_infos_via_ssh()
                self.log.debug("uuidcode={} - HPC_Infos afterwards: {}".format(uuidcode, hpc_infos))
            except:
                self.log.exception("uuidcode={} - Could not get HPC information via ssh for user {}".format(uuidcode, username))
        if type(hpc_infos) == str:
            if len(hpc_infos) == 0:
                hpc_infos = []
            else:
                hpc_infos = [hpc_infos]

        # Create a dictionary. So we only have to check for machines via UNICORE/X that are not known yet
        user_accs = get_user_dic(hpc_infos, self.resources)

        # Check for HPC Systems in self.unicore
        waitforaccupdate = self.get_hpc_infos_via_unicorex(uuidcode, username, user_accs, accesstoken)
        return {
                'name': username,
                'auth_state': {
                               'accesstoken': accesstoken,
                               'refreshtoken': refreshtoken,
                               'expire': expire,
                               'oauth_user': resp_json,
                               'user_dic': user_accs,
                               'useraccs_complete': not waitforaccupdate,
                               'scope': scope,
                               'login_handler': 'jscldap',
                               'errormsg': ''
                               }
                }

    async def jscusername_authenticate(self, handler, uuidcode, data=None):
        with open(self.unity_file, 'r') as f:
            unity = json.load(f)
        code = handler.get_argument("code")
        http_client = AsyncHTTPClient()
        params = dict(
            redirect_uri=self.get_callback_url(None, "JSCUsername"),
            code=code,
            grant_type='authorization_code'
        )
        params.update(self.extra_params)

        if self.jscusername_token_url:
            url = self.jscusername_token_url
        else:
            raise ValueError("uuidcode={} - Please set the JSCUSERNAME_TOKEN_URL environment variable".format(uuidcode))

        b64key = base64.b64encode(
            bytes(
                "{}:{}".format(unity[self.jscusername_token_url]['client_id'], unity[self.jscusername_token_url]['client_secret']),
                "utf8"
            )
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": self.j4j_user_agent,
            "Authorization": "Basic {}".format(b64key.decode("utf8"))
        }
        req = HTTPRequest(url,
                          method="POST",
                          headers=headers,
                          validate_cert=self.tls_verify,
                          body=urllib.parse.urlencode(params)
                          )

        resp = await http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))

        accesstoken = resp_json.get('access_token', None)
        refreshtoken = resp_json.get('refresh_token', None)
        token_type = resp_json.get('token_type', None)
        scope = resp_json.get('scope', '')
        if (isinstance(scope, str)):
            scope = scope.split(' ')

        # Determine who the logged in user is
        headers = {
            "Accept": "application/json",
            "User-Agent": self.j4j_user_agent,
            "Authorization": "{} {}".format(token_type, accesstoken)
        }
        url = url_concat(unity[self.jscusername_token_url]['links']['userinfo'], unity[self.jscusername_token_url].get('userdata_params', {}))

        req = HTTPRequest(url,
                          method=unity[self.jscusername_token_url].get('userdata_method', 'GET'),
                          headers=headers,
                          validate_cert=self.tls_verify)
        resp = await http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))

        username_key = unity[self.jscusername_authorize_url]['username_key']
        if not resp_json.get(username_key):
            self.log.error("uuidcode={} - OAuth user contains no key {}: {}".format(uuidcode, username_key, self.remove_secret(resp_json)))
            return

        req_exp = HTTPRequest(unity[self.jscusername_token_url]['links']['tokeninfo'],
                              method=unity[self.jscusername_token_url].get('tokeninfo_method', 'GET'),
                              headers=headers,
                              validate_cert=self.tls_verify)
        resp_exp = await http_client.fetch(req_exp)
        resp_json_exp = json.loads(resp_exp.body.decode('utf8', 'replace'))

        tokeninfo_exp_key = unity[self.jscusername_token_url].get('tokeninfo_exp_key', 'exp')
        if not resp_json_exp.get(tokeninfo_exp_key):
            self.log.error("uuidcode={} - Tokeninfo contains no key {}: {}".format(uuidcode, tokeninfo_exp_key, self.remove_secret(resp_json_exp)))
            return

        expire = str(resp_json_exp.get(tokeninfo_exp_key))
        username = resp_json.get(username_key).lower()
        username = self.normalize_username(username)
        self.log.info("uuidcode={}, action=login aai=jscusername, username={}".format(uuidcode, username))
        self.log.debug("uuidcode={}, action=revoke, username={}".format(uuidcode, username))
        try:
            with open(self.j4j_urls_paths, 'r') as f:
                j4j_paths = json.load(f)
            with open(j4j_paths.get('token', {}).get('orchestrator', '<no_token_found>'), 'r') as f:
                orchestrator_token = f.read().rstrip()
            json_dic = { 'accesstoken': accesstoken,
                         'refreshtoken': refreshtoken }
            header = {'Intern-Authorization': orchestrator_token,
                      'uuidcode': uuidcode,
                      'stopall': 'false',
                      'username': username,
                      'expire': expire,
                      'tokenurl': self.jscusername_token_url,
                      'authorizeurl': self.jscusername_token_url,
                      'allbutthese': 'true' }
            url = j4j_paths.get('orchestrator', {}).get('url_revoke', '<no_url_found>')
            with closing(requests.post(url,
                                      headers=header,
                                      json=json_dic,
                                      verify=False)) as r:
                if r.status_code != 202:
                    self.log.warning("uuidcode={} - Failed J4J_Orchestrator communication: {} {}".format(uuidcode, r.text, r.status_code))
        except:
            self.log.exception("uuidcode={} - Could not revoke old tokens for {}".format(uuidcode, username))

        # collect hpc infos with the known ways
        hpc_infos = resp_json.get(self.hpc_infos_key, '')

        # If it's empty and the username is an email address (and no train account) we can check for it via ssh
        if len(hpc_infos) == 0:
            pattern = re.compile("^([a-z0-9_\.-]+)@([\da-z\.-]+)\.([a-z\.]{2,6})$")
            if pattern.match(username):
                try:
                    self.log.debug("uuidcode={} - Try to get HPC_Infos via ssh".format(uuidcode))
                    hpc_infos = self.get_hpc_infos_via_ssh()
                    self.log.debug("uuidcode={} - HPC_Infos afterwards: {}".format(uuidcode, hpc_infos))
                except:
                    self.log.exception("uuidcode={} - Could not get HPC information via ssh for user {}".format(uuidcode, username))
        if type(hpc_infos) == str:
            if len(hpc_infos) == 0:
                hpc_infos = []
            else:
                hpc_infos = [hpc_infos]

        # Create a dictionary. So we only have to check for machines via UNICORE/X that are not known yet
        user_accs = get_user_dic(hpc_infos, self.resources)

        # Check for HPC Systems in self.unicore
        waitforaccupdate = self.get_hpc_infos_via_unicorex(uuidcode, username, user_accs, accesstoken)
        return {
                'name': username,
                'auth_state': {
                               'accesstoken': accesstoken,
                               'refreshtoken': refreshtoken,
                               'expire': expire,
                               'oauth_user': resp_json,
                               'user_dic': user_accs,
                               'useraccs_complete': not waitforaccupdate,
                               'scope': scope,
                               'login_handler': 'jscusername',
                               'errormsg': ''
                               }
                }

    def get_hpc_infos_via_unicorex(self, uuidcode, username, user_accs, accesstoken):
        try:
            with open(self.j4j_urls_paths, 'r') as f:
                j4j_paths = json.load(f)
            with open(j4j_paths.get('token', {}).get('orchestrator', '<no_token_found>'), 'r') as f:
                orchestrator_token = f.read().rstrip()
            with open(self.unicore, 'r') as f:
                unicore_file = json.load(f)
            machine_list = unicore_file.get('machines', [])
            # remove machines that are already served via Unity or ssh
            self.log.debug("uuidcode={} - Check user_acc keys: {}".format(uuidcode, user_accs.keys()))
            for m in user_accs.keys():
                if m in machine_list:
                    self.log.debug("uuidcode={} - Remove: {}".format(uuidcode, m))
                    machine_list.remove(m)
            if len(machine_list) > 0:
                machines = ' '.join(machine_list)
                header = {'Accept': "application/json",
                          'Intern-Authorization': orchestrator_token,
                          'uuidcode': uuidcode,
                          'username': username,
                          "User-Agent": self.j4j_user_agent,
                          'accesstoken': accesstoken,
                          'machines': machines}
                url = j4j_paths.get('orchestrator', {}).get('url_unicorex', '<no_url_found>')
                self.log.debug("uuidcode={} - GET to {} url with {}".format(uuidcode, url, header))
                with closing(requests.get(url,
                                          headers=header,
                                          verify=False)) as r:
                    if r.status_code == 204:
                        return True
                    else:
                        self.log.warning("uuidcode={} - Failed J4J_Orchestrator communication: {} {}".format(uuidcode, r.text, r.status_code))
                        return False
        except:
            self.log.exception("uuidcode={} - Could not check for other HPC accounts via UNICORE/X for {}".format(uuidcode, username))
        return False

    def get_hpc_infos_via_ssh(self, uuidcode, username):
        if username[-len("@fz-juelich.de"):] == '@fz-juelich.de':
            username = username[:-len("@fz-juelich.de")]
        cmd = ['ssh', '-i', self.hpc_infos_ssh_key, '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'LogLevel=ERROR', '{}@{}'.format(self.hpc_infos_ssh_user, self.hpc_infos_ssh_host), username]
        try:
            output = check_output(cmd, stderr=STDOUT, timeout=3, universal_newlines=True)
        except CalledProcessError:
            self.log.exception("uuidcode={} - No HPC infos for {}".format(uuidcode, username))
            return []
        hpc_infos = output.strip().split('\n')
        self.log.debug("uuidcode={} - Bare HPC_Infos: {}".format(uuidcode, hpc_infos))
        additional_lines = []
        try:
            if len(self.hpc_infos_add_queues) > 0:
                queues = {}
                for queue in self.hpc_infos_add_queues:
                    system, partition = queue.split('_')
                    if system not in queues.keys():
                        queues[system] = []
                    queues[system].append(partition)
                system_project = {}
                for entry in hpc_infos:
                    name, system, project, mail = entry.split(',')
                    if '_' in system:
                        split = system.split('_')
                        system = split[0]
                    if system not in system_project:
                        system_project[system] = []
                    if project in system_project[system]:
                        continue
                    for queue in queues.get(system, []):
                        additional_lines.append('{},{}_{},{},{}'.format(name, system, queue, project, mail))
                    system_project[system].append(project)
                hpc_infos.extend(additional_lines)
        except:
            self.log.exception("uuidcode={} - Could not add additional queues ({}) to hpc_infos of user {}".format(uuidcode, self.hpc_infos_add_queues, username))
        self.log.debug("uuidcode={} - Return: {}".format(uuidcode, hpc_infos))
        return hpc_infos
