'''
Created on May 10, 2019

@author: kreuzer
'''

import uuid
import os

from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.orm import APIToken, Spawner, User

class J4J_APICancelHandler(APIHandler):
    async def delete(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        self.log.info("{} - Cancel Spawn for server: {}".format(uuidcode, server_name))
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("{} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
        error = self.request.headers.get('Error', None)
        user = None
        if 'Authorization' in self.request.headers.keys():
            s = self.request.headers.get('Authorization').split()
            if len(s) == 2:
                found = APIToken.find(self.db, token=s[1])
                if found is not None:
                    user = self._user_from_orm(found.user)
        if not user:
            user = self.find_user(username)
        self.set_header('Content-Type', 'text/plain')
        if user:
            try:
                db_spawner = user.db.query(Spawner).filter(Spawner.name == server_name).filter(Spawner.user_id == user.orm_user.id).first()
                if db_spawner:
                    user.db.refresh(db_spawner)
                    user.spawners[server_name].load_state(db_spawner.state)
                if error:
                    db_user = user.db.query(User).filter(User.name == user.name).first()
                    if db_user:
                        user.db.refresh(db_user)
                        user.encrypted_auth_state = db_user.encrypted_auth_state
                    state = await user.get_auth_state()
                    new_state = {}
                    for key, value in state.items():
                        new_state[key] = value
                    new_state['errormsg'] = error
                    await user.save_auth_state(new_state)
                await user.spawners[server_name].cancel(uuidcode, self.request.headers.get('Stopped', 'false').lower() == 'true')
                self.set_status(202)
            except:
                self.log.exception("{} - {} Could not cancel the spawner: {}".format(user.name, uuidcode, server_name))
                self.set_status(501)
                self.write("Could not stop Server. Please look into the logs with the uuidcode: {}".format(uuidcode))
                self.flush()
        else:
            self.set_status(404)
            self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
            self.flush()
        return
