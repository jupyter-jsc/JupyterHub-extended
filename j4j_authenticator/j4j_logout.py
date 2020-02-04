from contextlib import closing
import json
import requests
import uuid
import os

from jupyterhub.handlers import LogoutHandler
from jupyterhub import orm


class J4J_LogoutHandler(LogoutHandler):
    async def handle_logout(self):
        """Custom user action during logout
        By default a no-op, this function should be overridden in subclasses
        to have JupyterHub take a custom action on logout.
        Override:
            Revoke tokens from Unity via J4J_Orchestrator.
        """
        user = self.current_user
        if user:
            uuidcode = uuid.uuid4().hex
            self.log.info("username={}, uuidcode={}, action=logout".format(user.name, uuidcode))
            state = await user.get_auth_state()
            if state:
                with open(user.authenticator.orchestrator_token_path, 'r') as f:
                    intern_token = f.read().rstrip()
                json_dic = {'accesstoken': state['accesstoken'],
                        'refreshtoken': state['refreshtoken']}
                header = {'Intern-Authorization': intern_token,
                          'uuidcode': uuidcode,
                          'stopall': 'true',
                          'username': user.name,
                          'escapedusername': user.escaped_name,
                          'expire': state['expire']}
                if state['login_handler'] == 'jscusername':
                    header['tokenurl'] = os.environ.get('JSCUSERNAME_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token')
                    header['authorizeurl'] = os.environ.get('JSCUSERNAME_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as-username/oauth2-authz')
                elif state['login_handler'] == 'jscldap':
                    header['tokenurl'] = os.environ.get('JSCLDAP_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token')
                    header['authorizeurl'] = os.environ.get('JSCLDAP_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as/oauth2-authz')
                elif state['login_handler'] == 'hdfaai':
                    header['tokenurl'] = os.environ.get('HDFAAI_TOKEN_URL', 'https://unity.helmholtz-data-federation.de/oauth2/token')
                    header['authorizeurl'] = os.environ.get('HDFAAI_AUTHORIZE_URL', 'https://unity.helmholtz-data-federation.de/oauth2-as/oauth2-authz')
                self.log.debug("uuidcode={} - User Spawners: {}".format(uuidcode, user.spawners))
                names = []
                db_spawner_list = user.db.query(orm.Spawner).filter(orm.Spawner.user_id == user.orm_user.id).all()
                for db_spawner in db_spawner_list:
                    names.append(db_spawner.name)
                for name in names:
                    self.log.debug("uuidcode={} - 'Stop' {}".format(uuidcode, name))
                    await user.spawners[name].cancel(uuidcode, True)
                self.log.debug("{} - Revoke access and refresh token - uuidcode={}".format(user.name, uuidcode))
                try:
                    with open(user.authenticator.j4j_urls_paths, 'r') as f:
                        urls = json.load(f)
                    url = urls.get('orchestrator', {}).get('url_revoke', '<no_url_found>')
                    with closing(requests.post(url,
                                               headers=header,
                                               json=json_dic,
                                               verify=False)) as r:
                        if r.status_code != 202:
                            self.log.warning("Failed J4J_Orchestrator communication: {} {}".format(r.text, r.status_code))
                except:
                    self.log.exception("{} - Could not revoke token".format(user.name))
                state['accesstoken'] = ''
                state['refreshtoken'] = ''
                state['expire'] = ''
                state['oauth_user'] = ''
                state['scope'] = []
                state['login_handler'] = ''
                await user.save_auth_state(state)
        return
