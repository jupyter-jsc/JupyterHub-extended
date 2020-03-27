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
        
class J4J_DPSHandler(BaseHandler):
    async def get(self):
        user = self.current_user        
        html = self.render_template(
                    'dps.html',
                    user=user)
        self.finish(html)
        
class J4J_ImprintHandler(BaseHandler):
    async def get(self):
        user = self.current_user        
        html = self.render_template(
                    'imprint.html',
                    user=user)
        self.finish(html)
        
class J4J_TestHandler(BaseHandler):
    async def get(self):
        user = self.current_user        
        html = self.render_template(
                    'test.html',
                    user=user)
        self.finish(html)
        
class J4J_ProjectsHandler(BaseHandler):
    async def get(self):
        user = self.current_user        
        html = self.render_template(
                    'projects.html',
                    user=user)
        self.finish(html)
        
class J4J_KernelHandler(BaseHandler):
    async def get(self):
        user = self.current_user        
        html = self.render_template(
                    'kernel.html',
                    user=user)
        self.finish(html)