'''
Created on May 10, 2019

@author: kreuzer
'''
import json
import time
import uuid
import smtplib
import os

from datetime import datetime
from email.mime.text import MIMEText

from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.orm import APIToken, Spawner

class J4J_APIStatusHandler(APIHandler):
    async def get(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        self.log.debug("uuidcode={} - GetStatus for server: servername={}".format(uuidcode, server_name))
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("uuidcode={} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
        user = None
        self.set_header('Content-Type', 'text/plain')
        if 'Authorization' in self.request.headers.keys():
            s = self.request.headers.get('Authorization').split()
            if len(s) == 2:
                found = APIToken.find(self.db, token=s[1])
                if found is not None:
                    user = self._user_from_orm(found.user)
        if not user:
            user = self.find_user(username)
        if user:
            try:
                db_spawner = user.db.query(Spawner).filter(Spawner.name == server_name).filter(Spawner.user_id == user.orm_user.id).first()
                if db_spawner:
                    user.db.refresh(db_spawner)
                    self.set_status(201)
                    if db_spawner.state['job_status']:
                        self.write(db_spawner.state['job_status'])
                    else:
                        self.write('None')
                else:
                    self.set_status(404)
                    self.write("No Spawner Class found")
            except:
                self.set_status(404)
                self.write("Could not load job_status from database")
        else:
            self.set_status(404)
            self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
        self.flush()
        return

    async def post(self, username, server_name=''):
        uuidcode = self.request.headers.get('uuidcode', None)
        if not uuidcode:
            uuidcode = uuid.uuid4().hex
        with open(os.environ.get('HUB_TOKEN_PATH', ''), 'r') as f:
            intern_token = f.read().rstrip()
        if self.request.headers.get('Intern-Authorization', '') != intern_token:
            self.log.warning("uuidcode={} - Could not validate Intern-Authorization".format(uuidcode))
            self.set_status(401)
            return
        data = self.request.body.decode("utf8")
        self.log.debug("uuidcode={} - Post Status Data: {}, Server_name: servername={}".format(uuidcode, data, server_name))
        self.set_header('Content-Type', 'text/plain')
        user = None
        if not data:
            self.set_status(400)
            self.write("Please send the Status in the body as json: { \"Status\": \"...\" }")
            self.flush()
            return
        if 'Authorization' in self.request.headers.keys():
            s = self.request.headers.get('Authorization').split()
            if len(s) == 2:
                found = APIToken.find(self.db, token=s[1])
                if found is not None:
                    user = self._user_from_orm(found.user)
        if not user:
            user = self.find_user(username)
        if user:
            # check if this is the case
            db_spawner = user.db.query(Spawner).filter(Spawner.name == server_name).filter(Spawner.user_id == user.orm_user.id).first()
            state = {}
            if db_spawner == None:
                # we do not know this server_name for this user, answer with 404
                self.log.debug("UID={} - uuidcode={} There is no server called servername={} for the user in the database".format(user.name, uuidcode, server_name))
                self.set_status(404)
                self.write("Server with name servername={} for user {} not found".format(server_name, user.name))
                self.flush()
            else:
                user.db.refresh(db_spawner)
                for key, value in db_spawner.state.items():
                    state[key] = value
                status = json.loads(data).get('Status', '<no status sent>')
                if status == 'dockerspawning':
                    # do nothing, just wait for Docker to finish
                    status = db_spawner.state.get('job_status', 'createjob')
                    db_progs_no = 0
                if status == 'submitunicorejob':
                    db_progs_no = 1
                elif status == 'waitforhostname':
                    db_progs_no = 2
                elif status == 'running':
                    db_progs_no = 3
                    if db_spawner.state.get('sendmail', False):
                        #msg = MIMEMultipart()
                        msg = MIMEText("The JupyterLab you requested has finished the spawn progress. You can visit it directly here: https://jupyter-jsc.fz-juelich.de/user/{}/{} . Or via the Control-Panel at https://jupyter-jsc.fz-juelich.de".format(user.name, server_name))
                        if db_spawner.user_options and 'system' in db_spawner.user_options.keys() and db_spawner.user_options['system']:
                            msg['Subject'] = "JupyterLab '{}' on {} is ready for you".format(server_name, db_spawner.user_options['system'])
                        else:
                            msg['Subject'] = "JupyterLab '{}' is ready for you".format(server_name)
                        msg['From'] = 'jupyter.jsc@fz-juelich.de'
                        msg['To'] = user.name
                        #body = MIMEText("The JupyterLab you requested has finished the spawn progress. You can visit it directly here: https://jupyter-jsc.fz-juelich.de/user/{}/{} . Or via the Control-Panel at https://jupyter-jsc.fz-juelich.de".format(user.name, server_name))
                        #msg.attach(body)
                        msg = msg.as_string()
                        s = smtplib.SMTP('mail.fz-juelich.de')
                        s.sendmail('jupyter.jsc@fz-juelich.de', user.name, msg)
                        s.quit()
                        self.log.debug("uuidcode={} - Send email to UID={} for servername={}".format(uuidcode, user.name, server_name))
                        state['sendmail'] = False
                elif status == 'stopped':
                    # spawner / job has stopped, so just 'stop' it for jupyterhub and everything's good
                    if str(type(user.spawners[server_name]._spawn_future)) == "<class '_asyncio.Task'>" and user.spawners[server_name]._spawn_future._state in ['PENDING']:
                        self.log.debug("uuidcode={} - UID={} Call User.cancel() for servername={}, because it's still pending".format(uuidcode, user.name, server_name))
                        await user.spawners[server_name].cancel(uuidcode, False)
                        self.log.debug("uuidcode={} - UID={} Call Stop after the job was cancelled to ensure that the memory state is right. servername={}".format(uuidcode, user.name, server_name))
                        await user.stop(server_name)
                    else:
                        self.log.debug("uuidcode={} - UID={} Call User.stop() for servername={}".format(uuidcode, user.name, server_name))
                        user.spawners[server_name].uuidcode_tmp = uuidcode
                        await user.stop(server_name)
                    self.set_status(201)
                    return
                else:
                    db_progs_no = -1
                    self.log.warning("UID={} - uuidcode={} Received unknown status '{}'.".format(user.name, uuidcode, status))
                state['db_progs_no'] = db_progs_no
                state['job_status'] = status
                state['last_status_update'] = time.time()
                # load state to spawner in memory
                user.spawners[server_name].load_state(db_spawner.state)
                #self.log.debug("{} - {} Set Database State to: {}".format(user.name, uuidcode, state))
                setattr(db_spawner, 'state', state)
                setattr(db_spawner, 'last_activity', datetime.utcnow())
                user.db.commit()
                self.set_status(201)
        else:
            self.set_status(404)
            self.write("User with token {} not found".format(self.request.headers.get('Authorization', None)))
            self.flush()
        return
