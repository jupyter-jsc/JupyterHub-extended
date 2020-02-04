'''
Created on May 10, 2019

@author: kreuzer
'''

import uuid
import socket
import os

from datetime import datetime
from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.orm import APIToken, Spawner

class J4J_APIProxyHandler(APIHandler):
    async def delete(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        self.log.debug("uuidcode={} - Remove proxys for server: {}".format(uuidcode, server_name))
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("uuidcode={} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
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
                self.log.debug("uuidcode={} - DB_spawner: {}".format(uuidcode, db_spawner))
                if db_spawner:
                    user.db.refresh(db_spawner)
                    #self.log.debug("{} - DB_spawner_state: {}".format(uuidcode, db_spawner.state))
                    user.spawners[server_name].load_state(db_spawner.state)
                    user.spawners[server_name].remove_proxys(uuidcode)
                    state = {}
                    for key, value in db_spawner.state.items():
                        state[key] = value
                    my_hostname = socket.gethostname()
                    state['hostname'] = my_hostname
                    self.log.debug("UID={} - uuidcode={} New Hostname for {}: {}".format(user.name, uuidcode, server_name, my_hostname))
                    setattr(db_spawner, 'state', state)
                    setattr(db_spawner, 'last_activity', datetime.utcnow())
                    user.db.commit()
                    user.spawners[server_name].setup_proxys(uuidcode)
                    self.set_status(200)
                else:
                    self.log.warning("UID={} - uuidcode={} There is no server with the name {} for the user in the database".format(user.name, uuidcode, server_name))
                    self.set_status(404)
                    self.write("Server with name {} for user UID={} not found".format(server_name, user.name))
                    self.flush()
            except:
                self.log.exception("UID={} - uuidcode={} Could not remove proxy routes for the spawner: {}".format(user.name, uuidcode, server_name))
                self.set_status(501)
                self.write("Could not remove proxy routes. Please look into the logs with the uuidcode: {}".format(uuidcode))
                self.flush()
        else:
            self.set_status(404)
            self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
            self.flush()
        return

    async def post(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        self.log.debug("uuidcode={} - Post Proxy Handler, server_name: {}".format(uuidcode, server_name))
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("uuidcode={} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
        self.set_header('Content-Type', 'text/plain')
        user = None
        if 'Authorization' in self.request.headers.keys():
            s = self.request.headers.get('Authorization').split()
            if len(s) == 2:
                found = APIToken.find(self.db, token=s[1])
                if found is not None:
                    user = self._user_from_orm(found.user)
        if not user:
            user = self.find_user(username)
        if user:
            # update database
            state = {}
            db_spawner = user.db.query(Spawner).filter(Spawner.name == server_name).filter(Spawner.user_id == user.orm_user.id).first()
            if db_spawner == None:
                self.log.warning("UID={} - uuidcode={} There is no server with the name {} for the user in the database".format(user.name, uuidcode, server_name))
                self.set_status(404)
                self.write("Server with name {} for user {} not found".format(server_name, user.name))
                self.flush()
            else:
                user.db.refresh(db_spawner)
                for key, value in db_spawner.state.items():
                    state[key] = value
                my_hostname = socket.gethostname()
                state['hostname'] = my_hostname
                self.log.debug("UID={} - uuidcode={} New Hostname for {}: {}".format(user.name, uuidcode, server_name, my_hostname))
                setattr(db_spawner, 'state', state)
                setattr(db_spawner, 'last_activity', datetime.utcnow())
                user.db.commit()
                user.spawners[server_name].load_state(db_spawner.state)
                user.spawners[server_name].setup_proxys(uuidcode)
                self.set_status(201)
        else:
            self.set_status(404)
            self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
            self.flush()
        return
