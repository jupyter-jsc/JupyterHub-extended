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
        if self.hub.base_url == '/hub/':
            proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_proxy:8001')
        else:
            proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_{}_proxy:8001'.format(self.hub.base_url[1:-len('/hub/')]))
        proxy_urls = []
        # first we remove all proxy routes that may exist from previous starts
        proxy_urls.append('/api/routes{baseurl}spawn-pending/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.escaped_name, servername=server_name))
        proxy_urls.append('/api/routes{baseurl}spawn/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.escaped_name, servername=server_name))
        proxy_urls.append('/api/routes{shortbaseurl}spawn/{username}/{servername}'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=user.escaped_name, servername=server_name))
        proxy_urls.append('/api/routes{baseurl}api/users/{username}/servers/{servername}/progress'.format(baseurl=self.hub.base_url, username=user.escaped_name, servername=server_name))
        proxy_urls.append('/api/routes{baseurl}api/jobstatus/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.escaped_name, servername=server_name))
        proxy_urls.append('/api/routes{baseurl}api/cancel/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.escaped_name, servername=server_name))
        try:
            if len(db_spawner.state.get('start_uuid', '')) > 0:
                proxy_urls.append('/api/routes{baseurl}api/uxnotification/{username}/{suidlen}_{suid}_{servername}'.format(baseurl=self.hub.base_url, username=user.escaped_name, suidlen=len(db_spawner.state.get('start_uuid')), suid=db_spawner.state.get('start_uuid'), servername=server_name))
        except:
            self.log.exception("Could not setup proxy route for uxnotification")
        # voila urls
        proxy_urls.append('/api/routes{shortbaseurl}{username}/{servername}/dashboard'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=user.escaped_name, servername=server_name))
        proxy_urls.append('/api/routes{shortbaseurl}user/{username}/{servername}/tree'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=user.escaped_name, servername=server_name))
        proxy_urls.append('/api/routes{shortbaseurl}user/{username}/{servername}/lab'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=user.escaped_name, servername=server_name))
        
        self.log.debug("UID={} - Remove Proxy routes: {}: {}".format(user.name, proxy_base_url, proxy_urls))
        for proxy_url in proxy_urls:
            try:
                with closing(requests.delete(proxy_base_url+proxy_url, headers=proxy_headers, verify=False)) as r:
                    if r.status_code != 204 and r.status_code != 404:
                        raise Exception('{} {}'.format(r.status_code, r.text))
            except:
                self.log.exception("UID={} - Could not delete route {} from proxy".format(user.name, proxy_url))
            
        
        hostname = socket.gethostname()
        target = urls.get('hub', {}).get('url_hostname', 'http://<hostname>:8081')
        target = target.replace('<hostname>', hostname)
        proxy_urls = []

        proxy_urls.append('/api/routes{baseurl}spawn-pending/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.name, servername=server_name))
        proxy_urls.append('/api/routes{baseurl}spawn/{username}/{servername}'.format(baseurl=self.hub.base_url, username=user.name, servername=server_name))
        proxy_urls.append('/api/routes{shortbaseurl}spawn/{username}/{servername}'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=user.name, servername=server_name))
        proxy_json = { 'target': target }
        if user.authenticator.multiple_instances:
            self.log.debug("UID={} - Add Proxy routes: {}: {}".format(user.name, proxy_base_url, proxy_urls))
            for proxy_url in proxy_urls:
                try:
                    with closing(requests.post(proxy_base_url+proxy_url, headers=proxy_headers, json=proxy_json, verify=False)) as r:
                        if r.status_code != 201:
                            raise Exception('{} {}'.format(r.status_code, r.text))
                except:
                    self.log.exception("UID={} : Could not add route {} to proxy. Target: {}".format(user.name, proxy_url, target))
        self.log.debug("UID={} - Redirect to: {}".format(user.name, next_url))
        self.redirect(next_url)
        return
