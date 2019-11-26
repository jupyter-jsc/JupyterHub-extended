import os
import uuid
import base64
import urllib
import json
import requests

from contextlib import closing
from traitlets import Unicode, Bool, List, Dict
from jupyterhub.handlers import BaseHandler
from jupyterhub import orm
from jupyterhub.objects import Server
from tornado.auth import OAuth2Mixin
from tornado.httpclient import HTTPRequest, AsyncHTTPClient
from tornado.httputil import url_concat
from oauthenticator.oauth2 import OAuthLoginHandler
from oauthenticator.generic import GenericOAuthenticator

from .j4j_logout import J4J_LogoutHandler

class JSCLDAPCallbackHandler(BaseHandler):
    pass

class JSCLDAPEnvMixin(OAuth2Mixin):
    _OAUTH_ACCESS_TOKEN_URL = os.environ.get('JSCLDAP_OAUTH2_TOKEN_URL', '')
    _OAUTH_AUTHORIZE_URL = os.environ.get('JSCLDAP_OAUTH2_AUTHORIZE_URL', '')

class JSCLDAPLoginHandler(OAuthLoginHandler, JSCLDAPEnvMixin):
    def get(self):
        redirect_uri = self.authenticator.get_callback_url(self, None, 'JSCLDAP')
        self.log.info('OAuth redirect: %r', redirect_uri)
        state = self.get_state()
        self.set_state_cookie(state)
        self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=self.authenticator.jscldap_client_id,
            scope=self.authenticator.jscldap_scope,
            extra_params={'state': state},
            response_type='code')

class BaseAuthenticator(GenericOAuthenticator):
    login_service = Unicode(
        "Jupyter@JSC Authenticator",
        config=True
    )

    multiple_instances = Bool(
        os.environ.get('MULTIPLE_INSTANCES', 'false').lower() in {'true', '1'},
        config=True,
        help="Is this JupyterHub instance running with other instances behind the same proxy with the same database?"
    )

    jscldap_client_id = Unicode(
        os.environ.get('JSCLDAP_CLIENT_ID', ''),
        config=True,
        help="Client ID for JSCLdap Login"
    )

    jscldap_client_secret = Unicode(
        os.environ.get('JSCLDAP_CLIENT_SECRET', ''),
        config=True,
        help="Client Secret for JSCLdap Login"
    )

    jscldap_scope = List(Unicode(), config=True,
        help="The OAuth scopes to request for JSCLdap."
    )

    jscldap_token_url = Unicode(
        os.environ.get('JSCLDAP_TOKEN_URL', ''),
        config=True,
        help="Access token endpoint URL for JSCLdap"
    )

    jscldap_userdata_url = Unicode(
        os.environ.get('JSCLDAP_USERDATA_URL', ''),
        config=True,
        help="Userdata url to get user data login information for JSCLdap"
    )

    jscldap_userdata_params = Dict(
        {},
        config=True,
        help="Userdata params to get user data login information for JSCLdap"
    )

    jscldap_userdata_method = Unicode(
        os.environ.get('JSCLDAP_USERDATA_METHOD', 'GET'),
        config=True,
        help="Userdata method to get user data login information for JSCLdap"
    )

    jscldap_username_key = Unicode(
        os.environ.get('JSCLDAP_USERNAME_KEY', 'username'),
        config=True,
        help="Userdata username key from returned json for JSCLDAP_USERDATA_URL"
    )

    jscldap_tokeninfo_url = Unicode(
        os.environ.get('JSCLDAP_TOKENINFO_URL', ''),
        config=True,
        help="Tokeninfo url to get tokeninfo data login information for JSCLdap"
    )

    jscldap_tokeninfo_method = Unicode(
        os.environ.get('JSCLDAP_TOKENINFO_METHOD', 'GET'),
        config = True,
        help="Tokeninfo method to get expire date of access token for JSCLdap"
    )

    jscldap_tokeninfo_exp_key = Unicode(
        os.environ.get('JSCLDAP_TOKENINFO_EXP_KEY', 'exp'),
        config=True,
        help="Tokeninfo exp key from returned json for JSCLDAP_TOKENINFO_URL"
    )

    hpc_infos_key = Unicode(
        os.environ.get('OAUTH2_HPC_INFOS_KEY', ''),
        config=True,
        help="Userdata hpc_infos key from returned json for USERDATA_URL"
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

    partitions_path = Unicode( # should be removed
        os.environ.get('PARTITIONS_PATH', ''),
        config = True,
        help = "Path to the filled_resources file"
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

    login_handler = [JSCLDAPLoginHandler]
    logout_handler = J4J_LogoutHandler
    callback_handler = [JSCLDAPCallbackHandler]

    def get_handlers(self, app):
        return [
            (r'/jscldap_login', self.login_handler[0]),
            (r'/jscldap_callback', self.callback_handler[0]),
            (r'/logout', self.logout_handler)
        ]

    def get_callback_url(self, handler=None, authenticator_name="None"):
        if authenticator_name == 'JSCLDAP':
            return self.jscldap_callback_url

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
        self.log.debug("{} - Update memory of spawner. Called by: {}".format(user.name, caller))
        with open(self.j4j_urls_paths, 'r') as f:
            j4j_paths = json.load(f)
        resources_filled = j4j_paths.get('hub', {}).get('path_partitions', '<no_path_found>')
        db_user = user.db.query(orm.User).filter(orm.User.name == user.name).first()
        user.db.refresh(db_user)
        db_spawner_all = user.db.query(orm.Spawner).filter(orm.Spawner.user_id == db_user.id).all()
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
                spawner[db_spawner.name]['spawnable'] = db_spawner.user_options.get('system').upper() in resources_filled.keys() or db_spawner.user_options.get('system').upper() == 'DOCKER'
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
            # yield wrapper if it exists (server may be active)
            user.spawners[name].load_state(spawner[name]['state'])
            if user.spawners[name].active:
                #self.log.debug("{} - Spawner {} is in memory and active".format(user.name, name))
                if not spawner[name]['active']:
                    uuidcode = uuid.uuid4().hex
                    #self.log.debug("{} - Spawner {} should not be active. Delete it: {}".format(user.name, name, uuidcode))
                    await user.spawners[name].cancel(uuidcode, True)
                else:
                    self.log.debug("{} - Spawner {} should be active. Check server_url and port".format(user.name, name))
                    db_server = user.db.query(orm.Server).filter(orm.Server.id == spawner[name]['server_id']).first()
                    user.db.refresh(db_server)
                    if db_server.base_url != user.spawners[name].server.base_url or db_server.port != user.spawners[name].server.port:
                        self.log.debug("Bind_URLs from server {} are different between Database {} and memory {}. Trust the database and delete the own server".format(name, db_server, user.spawners[name].server))
                        old_server = user.db.query(orm.Server).filter(orm.Server.id == user.spawners[name].orm_spawner.server_id).first()
                        if old_server:
                            self.log.debug("Delete old server {} from database".format(old_server))
                            user.db.expunge(old_server)
                        user.spawners[name].orm_spawner.server = None
                        user.spawners[name].server = Server(orm_server=db_server)
            else:
                #self.log.debug("{} - Spawner {} is in memory and not active".format(user.name, name))
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
                    #self.log.debug("{} - Spawner {} should not be active. Everything's fine".format(user.name, name))
                if self.spawnable_dic.get(user.name) == None:
                    self.spawnable_dic[user.name] = {}
                user.spawners[name].spawnable = spawner[name]['spawnable']
                user.orm_user.orm_spawners.get(name).spawnable = spawner[name]['spawnable']
                self.spawnable_dic[user.name][name] = spawner[name]['spawnable']
        if len(to_pop_list) > 0:
            for name in to_pop_list:
                self.log.debug("{} - Remove {} from memory".format(user.name, name))
                user.spawners.pop(name, None)
        for dirty_obj in user.db.dirty:
            self.log.debug("{} - Refresh {}".format(user.name, dirty_obj))
            self.db.refresh(dirty_obj)            
                    
    spawnable_dic = {}
    def spawnable(self, user_name, server_name):
        if user_name in self.spawnable_dic.keys() and server_name in self.spawnable_dic[user_name].keys():
            return self.spawnable_dic[user_name][server_name]
        else:
            return True

    async def authenticate(self, handler, data=None):
        uuidcode = uuid.uuid4().hex
        self.log.debug("{} - Login attempt".format(uuidcode))
        if (handler.__class__.__name__ == "JSCLDAPCallbackHandler"):
            return await self.jscldap_authenticate(handler, uuidcode, data)
        else:
            self.log.warning("Unknown CallbackHandler: {}".format(handler.__class__))
            return "Username"

    async def jscldap_authenticate(self, handler, uuidcode, data=None):
        code = handler.get_argument("code")
        http_client = AsyncHTTPClient()
        params = dict(
            redirect_uri=self.get_callback_url("JSCLDAP"),
            code=code,
            grant_type='authorization_code'
        )
        params.update(self.extra_params)

        if self.jscldap_token_url:
            url = self.jscldap_token_url
        else:
            raise ValueError("{} - Please set the JSCLDAP_TOKEN_URL environment variable".format(uuidcode))

        b64key = base64.b64encode(
            bytes(
                "{}:{}".format(self.jscldap_client_id, self.jscldap_client_secret),
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

        resp = yield http_client.fetch(req)
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
        if self.jscldap_userdata_url:
            url = url_concat(self.jscldap_userdata_url, self.jscldap_userdata_params)
        else:
            raise ValueError("{} - Please set the JSCLDAP_USERDATA_URL environment variable".format(uuidcode))

        req = HTTPRequest(url,
                          method=self.jscldap_userdata_method,
                          headers=headers,
                          validate_cert=self.tls_verify)
        resp = yield http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))

        if not resp_json.get(self.jscldap_username_key):
            self.log.error("{} - OAuth user contains no key {}: {}".format(uuidcode, self.jscldap_username_key, self.remove_secret(resp_json)))
            return

        if self.jscldap_tokeninfo_url:
            url = self.jscldap_tokeninfo_url
        else:
            raise ValueError("{} - Please set the JSCLDAP_TOKENINFO_URL environment variable".format(uuidcode))

        req_exp = HTTPRequest(url,
                              method=self.jscldap_tokeninfo_method,
                              headers=headers,
                              validate_cert=self.tls_verify)
        resp_exp = yield http_client.fetch(req_exp)
        resp_json_exp = json.loads(resp_exp.body.decode('utf8', 'replace'))

        if not resp_json_exp.get(self.jscldap_tokeninfo_exp_key):
            self.log.error("{} - Tokeninfo contains no key {}: {}".format(uuidcode, self.jscldap_tokeninfo_exp_key, self.remove_secret(resp_json_exp)))
            return

        expire = str(resp_json_exp.get(self.jscldap_tokeninfo_exp_key))
        username = resp_json.get(self.jscldap_username_key).split('=')[1]
        username = self.normalize_username(username)
        self.log.info("{} - Login: {} -> {} logged in.".format(uuidcode, resp_json.get(self.jscldap_username_key), username))
        self.log.debug("{} - Revoke old tokens for user {}".format(uuidcode, username))
        try:
            with open(self.j4j_urls_paths, 'r') as f:
                j4j_paths = json.load(f)
            with open(self.j4j_paths.get('token', {}).get('orchestrator', '<no_token_found>'), 'r') as f:
                orchestrator_token = f.read().rstrip()
            json_dic = { 'accesstoken': accesstoken,
                         'refreshtoken': refreshtoken }
            header = {'Intern-Authorization': orchestrator_token,
                      'uuidcode': uuidcode,
                      'stopall': 'false',
                      'username': username,
                      'expire': expire,
                      'allbutthese': 'true' }
            url = j4j_paths.get('orchestrator', {}).get('url_revoke', '<no_url_found>')
            with closing(requests.post(url,
                                      headers=header,
                                      json=json_dic,
                                      verify=False)) as r:
                if r.status_code != 202:
                    self.log.warning("{} - Failed J4J_Orchestrator communication: {} {}".format(uuidcode, r.text, r.status_code))
        except:
            self.log.exception("{} - Could not revoke old tokens for {}".format(uuidcode, username))

        return {
                'name': username,
                'auth_state': {
                               'accesstoken': accesstoken,
                               'refreshtoken': refreshtoken,
                               'expire': expire,
                               'oauth_user': resp_json,
                               'scope': scope,
                               'errormsg': ''
                               }
                }
