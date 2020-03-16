'''
Created on May 10, 2019

@author: kreuzer
'''

from jupyterhub.handlers.base import BaseHandler


class J4J_ToSHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        
        html = self.render_template(
                    'tos.html',
                    user=user)
        self.finish(html)