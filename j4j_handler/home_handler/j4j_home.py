'''
Created on May 10, 2019

@author: kreuzer
'''

from jupyterhub.handlers.pages import HomeHandler
from jupyterhub.utils import url_path_join
from tornado import web

class J4J_HomeHandler(HomeHandler):
    @web.authenticated
    async def get(self):
        user = self.current_user
        await user.authenticator.update_mem(user, "HomeHandler")
        if user.running:
            # trigger poll_and_notify event in case of a server that died
            await user.spawner.poll_and_notify()
        # send the user to /spawn if they have no active servers,
        # to establish that this is an explicit spawn request rather
        # than an implicit one, which can be caused by any link to `/user/:name(/:server_name)`
        if user.active:
            url = url_path_join(self.base_url, 'user', user.name)
        else:
            url = url_path_join(self.hub.base_url, 'spawn', user.name)
        html = self.render_template(
                    'home.html',
                    user=user,
                    url=url,
                    allow_named_servers=self.allow_named_servers,
                    named_server_limit_per_user=self.named_server_limit_per_user,
                    url_path_join=url_path_join,
                    # can't use user.spawners because the stop method of User pops named servers from user.spawners when they're stopped
                    spawners=user._orm_spawners,
                    default_server=user.spawner,
                    spawnable_dic=user.authenticator.spawnable_dic.get(user.name, {}))
        self.finish(html)

