'''
Created on May 10, 2019

@author: kreuzer
'''
import uuid
import requests
import jwt
import json

from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from contextlib import closing

from jupyterhub.orm import Spawner
from jupyterhub.utils import url_path_join
from jupyterhub.apihandlers.base import APIHandler

class J4J_APIUXHandler(APIHandler):
    async def post(self, username, server_name=''):
        uuidcode = uuid.uuid4().hex
        self.log.debug("uuidcode={} - UX Handler for username={} servername={}".format(uuidcode, username, server_name))
        user = self.find_user(username)
        self.log.debug("uuidcode={} - UX Handler: Headers: {}".format(uuidcode, self.request.headers))
        self.log.debug("uuidcode={} - UX Handler: Body: {}".format(uuidcode, self.request.body.decode("utf8")))
        if not user:
            self.set_status(404)
            self.write("User with name {} not found".format(username))
            self.flush()
            return
        data = self.request.body.decode("utf8")
        jdata = json.loads(data)
        header = self.request.headers
        auth = header.get('Authorization', None)
        if not auth:
            self.set_status(401)
            self.write("No Authorization Header found")
            self.flush()
            return
        
        system = ""
        cert_url = ""
        cert_path = ""
        cert = ""
        try:
            kernelurl = jdata.get('href', '')
            ux_info_path = user.authenticator.unicore_infos
            with open(ux_info_path, 'r') as f:
                ux_info = json.load(f)
            for isystem, infos in ux_info.items():
                if kernelurl.startswith(infos.get('link', '...')):
                    system = isystem
                    cert_url = url_path_join(infos.get('link'), 'certificate')
                    cert_path = infos.get('certificate', False)
                    break
            if system != "":
                with closing(requests.get(cert_url, headers={'accept': 'text/plain'}, verify=cert_path)) as r:
                    cert = r.content
            
            bearer = auth.split()[1]
            cert_obj = load_pem_x509_certificate(cert, default_backend())            
            #jwt_dic = jwt.decode(bearer, cert_obj.public_key(), options={'verify_exp': False})
            jwt_dic = jwt.decode(bearer, cert_obj.public_key())
            self.log.debug("uuidcode={} - Tokeninfos decrypted: {}".format(uuidcode, jwt_dic))
        except:
            self.log.exception("uuidcode={} - Could not verify token {} with public key for UNICORE/X {}".format(uuidcode, auth, system))
            self.set_status(401)
            return
        if jdata.get('status', '') == 'RUNNING':
            # do nothing. We checked it previously and already know that
            self.set_status(204)
            return
        elif jdata.get('status', '') in ['SUCCESSFUL', 'FAILED', 'DONE']:
            if jdata.get('statusmessage', '') == 'Job was aborted by the user.':
                # do nothing. We've killed this job via Jupyter-jsc and therefore know this status already
                self.set_status(202)
                return
            self.log.info("uuidcode={} - Job is finished. Stop it via JupyterHub.".format(uuidcode))
            try:
                try:
                    uuidlen = server_name.split('_')[0]
                    strlen = len(uuidlen) + int(uuidlen) + 2
                    start_uuid = server_name.split('_')[1]
                    server_name = server_name[strlen:]
                except:
                    start_uuid = None
                    self.log.exception("uuidcode={} - Looks like servername {} has no uuid in it".format(uuidcode, server_name))
                db_spawner = user.db.query(Spawner).filter(Spawner.name == server_name).filter(Spawner.user_id == user.orm_user.id).first()
                if db_spawner:
                    user.db.refresh(db_spawner)
                    user.spawners[server_name].load_state(db_spawner.state)
                if start_uuid:
                    if user.spawners[server_name].start_uuid != start_uuid:
                        self.log.info("uuidcode={} - That's not the uuid this server was started with. So we ignore this U/X notification, because it's for an already stopped server.".format(uuidcode))
                        self.set_status(200)
                        return
                if user.spawners[server_name].service == "Dashboard" and jdata.get('exitCode', '') == "127":
                    try:
                        with open(user.authenticator.dashboards_path, 'r') as f:
                            dashboards_info = json.load(f)
                    except:
                        self.log.exception("uuidcode={} - Could not load dashboard infos".format(uuidcode))
                        dashboards_info = {}
                    em = dashboards_info.get(user.spawners[server_name].dashboard, {}).get(user.spawners[server_name].system, {}).get('failmessage', 'Something went wrong :(')
                    self.log.debug("uuidcode={} - Set error message for user to: {}".format(uuidcode, em))
                    user.spawners[server_name].error_message = em
                await user.spawners[server_name].cancel(uuidcode, False)
                self.set_status(202)
            except:
                self.log.exception("UID={} - uuidcode={} Could not cancel the spawner: {}".format(user.name, uuidcode, server_name))
                self.set_status(501)
                self.write("Could not stop Server. Please look into the logs with the uuidcode: uuidcode={}".format(uuidcode))
                self.flush()
        else:
            self.log.debug("uuidcode={} UX Handler: Unknown status. Insert reaction to this status: {}".format(uuidcode, jdata))
        return