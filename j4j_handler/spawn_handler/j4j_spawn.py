'''
Created on May 10, 2019

@author: kreuzer
'''

import uuid
import requests
import json
import socket

from contextlib import closing
from jupyterhub.orm import Spawner
from jupyterhub.handlers.pages import SpawnHandler
from tornado import web


class J4J_SpawnHandler(SpawnHandler):
    @web.authenticated
    async def get(self, for_user=None, server_name=''):
        """Handle /hub/spawn-pending/:user/:server
        One and only purpose:
        - wait for pending spawn
        - serve progress bar
        - redirect to /user/:name when ready
        - show error if spawn failed
        Functionality split out of /user/:name handler to
        have clearer behavior at the right time.
        Requests for this URL will never trigger any actions
        such as spawning new servers.
        """
        user = current_user = self.current_user
        if for_user is not None and for_user != current_user.name:
            if not current_user.admin:
                raise web.HTTPError(
                    403, "Only admins can spawn on behalf of other users"
                )
            user = self.find_user(for_user)
            if user is None:
                raise web.HTTPError(404, "No such user: %s" % for_user)
        service = self.get_argument("service", "JupyterLab", True)
        if server_name == '':
            server_name = uuid.uuid4().hex
            server_name = service + '_' + server_name[:8]
        else:
            server_name = server_name.lower()
            server_name_copy = server_name
            allowed = 'abcdefghijklmnopqrstuvwxyz_0123456789'
            for c in server_name_copy:
                if c not in allowed:
                    server_name = server_name.replace(c, '')
        next_url = self.get_next_url(user, default=user.server_url(server_name))
        db_spawner = user.db.query(Spawner).filter(Spawner.user_id == user.orm_user.id).filter(Spawner.name == server_name).first()
        if db_spawner:
            user.db.refresh(db_spawner)
        if not db_spawner or not db_spawner.server_id:
            next_url = next_url.replace('/user/', '/spawn/')
        self.redirect(next_url)

        # define the service for the Spawner Class
        state = await user.get_auth_state()
        if 'spawner_service' not in state.keys():
            state['spawner_service'] = {}
        state['spawner_service'][server_name] = service
        await user.save_auth_state(state)        

        # add proxy route for /hub/spawn/{user.name}/{server_name} and /hub/spawn-pending/{user.name}/{server_name}
        with open(user.authenticator.j4j_urls_paths, 'r') as f:
            urls = json.load(f)
        with open(user.authenticator.proxy_secret, 'r') as f:
            proxy_secret = f.read().strip()
        proxy_secret = proxy_secret.strip()[len('export CONFIGPROXY_AUTH_TOKEN='):]
        proxy_headers = {'Authorization': 'token {}'.format(proxy_secret)}
        hostname = socket.gethostname()
        target = urls.get('hub', {}).get('url_hostname', 'http://<hostname>:8081')
        target = target.replace('<hostname>', hostname)
        proxy_urls = []
        if self.hub.base_url == '/hub/':
            proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_proxy:8001')
        else:
            proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_{}_proxy:8001'.format(self.hub.base_url[1:-len('/hub/')]))
        proxy_urls.append('/api/routes{baseurl}spawn-pending/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.name, servername=server_name))
        proxy_urls.append('/api/routes{baseurl}spawn/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.name, servername=server_name))
        proxy_urls.append('/api/routes{shortbaseurl}spawn/{username}/{servername}'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=user.name, servername=server_name))
        proxy_json = { 'target': target }
        for proxy_url in proxy_urls:
            with closing(requests.post(proxy_base_url+proxy_url, headers=proxy_headers, json=proxy_json, verify=False)) as r:
                if r.status_code != 201:
                    raise Exception('{} {}'.format(r.status_code, r.text))
            self.log.debug("UID={} : {} - Added route to proxy: {} => {}".format(user.name, server_name, proxy_url, target))
        return
