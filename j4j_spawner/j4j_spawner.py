'''
Created on May 17, 2019

@author: Tim Kreuzer
'''

import requests
import uuid
import json
import socket

from traitlets import Unicode, Dict
from asyncio import sleep
from datetime import datetime
from contextlib import closing

from async_generator import async_generator, yield_

from jupyterhub.spawner import Spawner
from jupyterhub import orm
from jupyterhub.utils import url_path_join


from .utils import reservations, create_spawn_data, create_spawn_header
from .html import create_html
from .communication import j4j_orchestrator_request
from .file_loads import get_token
from j4j_spawner.utils import get_maintenance

class J4J_Spawner(Spawner):
    # Variables for the options_form
    #partitions_path = Unicode(config=True, help='')
    reservation_paths = Dict(config=True, help='')
    style_path = Unicode(config=True, help='')
    dockerimages_path = Unicode(config=True, help='')
    project_checkbox_path = Unicode(config=True, help='')
    nodes_path = Unicode(config=True, help='')
    html_code = ""

    # Variables for the jupyter application
    job_status = None
    progs_messages_all = [
                      {"progress": 20, "html_message": "Creating a <a href=\"https://www.unicore.eu\">UNICORE</a> Job." },
                      {"progress": 40, "html_message": "Submitting Job to <a href=\"https://www.unicore.eu\">UNICORE</a>." },
                      {"progress": 60, "html_message": "Waiting until your <system>-Job is started." },
                      {"progress": 80, "html_message": "Load modules on HPC System. Waiting for an answer of your JupyterLab."}
                     ]
    progs_no = 0
    db_progs_no = -1
    hostname = None
    stopped = False
    uuidcode_tmp = None
    sendmail = False
    login_handler = ''

    def clear_state(self):
        """clear any state (called after shutdown)"""
        super(J4J_Spawner, self).clear_state()
        self.job_status = None
        self.db_progs_no = -1
        self.progs_no = 0
        self.hostname = None
        self.uuidcode_tmp = None
        self.stopped = False
        self.api_token = ''
        self.sendmail = False
        self.login_handler = ''

    def load_state(self, state):
        """load state from the database"""
        super(J4J_Spawner, self).load_state(state)
        if state:
            self.job_status = state.get('job_status', None)
            self.db_progs_no = state.get('db_progs_no', -1)
            self.hostname = state.get('hostname', None)
            self.api_token = state.get('api_token', '')
            self.sendmail = state.get('sendmail', False)
            self.login_handler = state.get('loginhandler', '')
        else:
            self.job_status = None
            self.db_progs_no = -1
            self.hostname = None
            self.api_token = ''
            self.sendmail = False
            self.login_handler = ''

    def get_state(self):
        """get the current state"""
        state = super(J4J_Spawner, self).get_state()
        state['job_status'] = self.job_status
        state['db_progs_no'] = self.db_progs_no
        state['hostname'] = self.hostname
        state['api_token'] = self.api_token
        state['sendmail'] = self.sendmail
        state['loginhandler'] = self.login_handler
        return state

    @property
    def started(self):
        return self.orm_spawner.started

    @async_generator
    async def progress(self):
        while self.progs_no < 4:
            db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.name == self.name).filter(orm.Spawner.user_id == self.user.orm_user.id).first()
            if not db_spawner:
                self.log.debug("{} - {} not found.".format(self._log_name.lower(), self.name))
                return
            self.user.db.refresh(db_spawner)
            self.load_state(db_spawner.state)
            if db_spawner.user_options.get('system', 'none').lower() == 'docker':
                await yield_({'progress': 50, 'html_message': 'Start JupyterLab in a virtual Machine'})
                return
            while self.progs_no <= self.db_progs_no:
                s_orig = self.progs_messages_all[self.progs_no]
                s = {}
                for key, value in s_orig.items():
                    s[key] = value
                if '<system>' in s['html_message']:
                    if 'system' in db_spawner.user_options:
                        s['html_message'] = s['html_message'].replace('<system>', db_spawner.user_options['system'])
                if '<account>' in s['html_message']:
                    if 'account' in db_spawner.user_options:
                        s['html_message'] = s['html_message'].replace('<account>', db_spawner.user_options['account'])
                if '<project>' in s['html_message']:
                    if 'project' in db_spawner.user_options:
                        s['html_message'] = s['html_message'].replace('<project>', db_spawner.user_options['project'])
                await yield_(s)
                self.progs_no += 1
            db_spawner = None
            await sleep(1)

    def setup_proxys(self, uuidcode, urls=None):
        # add routes to proxy
        try:
            if not urls:
                with open(self.user.authenticator.j4j_urls_paths, 'r') as f:
                    urls = json.load(f)
            with open(self.user.authenticator.proxy_secret, 'r') as f:
                proxy_secret = f.read().strip()
            proxy_secret = proxy_secret.strip()[len('export CONFIGPROXY_AUTH_TOKEN='):]
            if not self.hostname:
                self.hostname = socket.gethostname()
            proxy_headers = {'Authorization': 'token {}'.format(proxy_secret)}
            target = urls.get('hub', {}).get('url_hostname', 'http://<hostname>:8081')
            target = target.replace('<hostname>', self.hostname)
            proxy_urls = []
            self.log.debug("{} - BaseUrl: {} - {}".format(self._log_name.lower(), self.hub.base_url, self.hub.base_url != '/'))
            if self.hub.base_url == '/hub/':
                proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_proxy:8001')
            else:
                proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_{}_proxy:8001'.format(self.hub.base_url[1:-len('/hub/')]))
            proxy_urls.append('/api/routes{baseurl}spawn-pending/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}spawn/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{shortbaseurl}spawn/{username}/{servername}'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}api/users/{username}/servers/{servername}/progress'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}api/jobstatus/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}api/cancel/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_json = { 'target': target }
            for proxy_url in proxy_urls:
                with closing(requests.post(proxy_base_url+proxy_url, headers=proxy_headers, json=proxy_json, verify=False)) as r:
                    if r.status_code != 201:
                        raise Exception('{} {} {}'.format(proxy_base_url+proxy_url, r.status_code, r.text))
                self.log.debug("{} - {} Added route to proxy: {} => {}".format(self._log_name.lower(), uuidcode, proxy_url, target))
        except:
            self.log.exception("{} - {} Could not add route to proxy".format(self._log_name.lower(), uuidcode))

    def remove_proxys(self, uuidcode, urls=None):
        # delete route from proxy
        self.log.debug("{} - {} - Remove all proxy routes".format(self._log_name.lower(), uuidcode))
        proxy_urls = []
        self.log.debug("{} - BaseUrl: {} - {}".format(self._log_name.lower(), self.hub.base_url, self.hub.base_url != '/'))
        try:
            if not urls:
                with open(self.user.authenticator.j4j_urls_paths, 'r') as f:
                    urls = json.load(f)
            if self.hub.base_url == '/hub/':
                proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_proxy:8001')
            else:
                proxy_base_url = urls.get('hub', {}).get('url_api', 'http://j4j_{}_proxy:8001'.format(self.hub.base_url[1:-len('/hub/')]))
            proxy_urls.append('/api/routes{baseurl}spawn-pending/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}spawn/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{shortbaseurl}spawn/{username}/{servername}'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}api/users/{username}/servers/{servername}/progress'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}api/jobstatus/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            proxy_urls.append('/api/routes{baseurl}api/cancel/{username}/{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, servername=self.name))
            with open(self.user.authenticator.proxy_secret, 'r') as f:
                proxy_secret = f.read().strip()
            proxy_secret = proxy_secret.strip()[len('export CONFIGPROXY_AUTH_TOKEN='):]
            proxy_headers = {'Authorization': 'token {}'.format(proxy_secret)}
            for proxy_url in proxy_urls:
                try:
                    with closing(requests.delete(proxy_base_url+proxy_url, headers=proxy_headers, verify=False)) as r:
                        if r.status_code != 204 and r.status_code != 404:
                            raise Exception('{} {}'.format(r.status_code, r.text))
                    self.log.debug("{} - {} Delete route from proxy: {}".format(self._log_name.lower(), uuidcode, proxy_url))
                except:
                    self.log.exception("{} - {} Could not delete route {} from proxy".format(self._log_name.lower(), uuidcode, proxy_url))
        except:
            self.log.exception("{} -{} Could not delete route from proxy".format(self._log_name.lower(), uuidcode))

    async def start(self):
        if 'system' not in self.user_options:
            # This errors occures, if you are able to trigger this function, without having your uids loaded first (Example: Open Home, load users, restart Hub, press Spawn)
            raise Exception("Not allowed")

        # Create uuidcode to track this specific Call through the webservices
        uuidcode = uuid.uuid4().hex
        self.log.info("{} - Start JupyterLab. UUID: {} . Options: {}".format(self._log_name.lower(), uuidcode, self.user_options))
        # get a few JupyterHub variables, which we will need to create spawn_header and spawn_data
        db_user = self.user.db.query(orm.User).filter(orm.User.name == self.user.name).first()
        if db_user:
            self.user.db.refresh(db_user)
            self.user.encrypted_auth_state = db_user.encrypted_auth_state
        state = await self.user.get_auth_state()
        env = self.get_env()
        self.log.debug("{} - Environment: {}".format(uuidcode, env))
        if env['JUPYTERHUB_API_TOKEN'] == "":
            env = self.get_env()
            self.log.debug("{} - Environment had no token, second try: {}".format(uuidcode, env))
            if env['JUPYTERHUB_API_TOKEN'] == "":
                self.log.debug("{} - Still nothing. Try to do it manually".format(uuidcode))
                try:
                    username_at_split = self.user.name.split('@')
                    env = {
                           'PATH': '/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                           'LANG': 'C.UTF-8',
                           'JUPYTERHUB_CLIENT_ID': 'jupyterhub-user-{}%40{}-{}'.format(username_at_split[0], username_at_split[1], self.name),
                           'JUPYTERHUB_HOST': '',
                           'JUPYTERHUB_OAUTH_CALLBACK_URL': '/user/{}/{}/oauth_callback'.format(self.user.name, self.name),
                           'JUPYTERHUB_USER': '{}'.format(self.user.name),
                           'JUPYTERHUB_SERVER_NAME': '{}'.format(self.name),
                           'JUPYTERHUB_API_URL': 'http://j4j_hub:8081/hub/api',
                           'JUPYTERHUB_ACTIVITY_URL': 'http://j4j_hub:8081/hub/api/users/{}/activity'.format(self.user.name),
                           'JUPYTERHUB_BASE_URL': '/',
                           'JUPYTERHUB_SERVICE_PREFIX': '/user/{}/{}/'.format(self.user.name, self.name)
                    }
                    base_url = url_path_join(self.user.base_url, self.name) + '/'
                    note = "Server at %s" % base_url
                    self.api_token = self.user.new_api_token(note=note)
                    self.user.db.commit()
                    env['JUPYTERHUB_API_TOKEN'] = self.api_token
                    env['JPY_API_TOKEN'] = env['JUPYTERHUB_API_TOKEN']
                    self.log.debug("{} - New Environment: {}".format(uuidcode, env))
                except:
                    self.log.exception("{} - Could not create own environment".format(uuidcode))
                    raise Exception("{} - Could not load environment. Please try again".format(uuidcode))
        if self.user_options.get('system').lower() != 'docker':
            if 'JUPYTERHUB_ACTIVITY_URL' in env:
                del env['JUPYTERHUB_ACTIVITY_URL']
            if 'JUPYTERHUB_API_URL' in env:
                del env['JUPYTERHUB_API_URL']
        else:
            env['hpcaccounts'] = state.get('oauth_user').get(self.user.authenticator.hpc_infos_key)
        self.hostname = socket.gethostname()
        #self.port = random_port()

        # Create Header and Data for the first Post Call to J4J_Orchestrator
        spawn_header = create_spawn_header(uuidcode,
                                           state.get('expire'),
                                           state.get('refreshtoken'),
                                           env['JUPYTERHUB_API_TOKEN'],
                                           state.get('accesstoken'),
                                           self.user_options.get('account'),
                                           self.user_options.get('project'),
                                           self._log_name.lower(),
                                           self.user.escaped_name,
                                           self.user.authenticator.orchestrator_token_path,
                                           state.get('login_handler', ''))
        spawn_data = create_spawn_data(self._log_name.lower(),
                                       env,
                                       self.user_options.get('partition'),
                                       self.user_options.get('reservation'),
                                       self.user_options.get('Resources', {}),
                                       self.user_options.get('system'),
                                       self.user_options.get('Checkboxes', []))
        self.login_handler = state.get('login_handler', '')

        try:
            with open(self.user.authenticator.j4j_urls_paths, 'r') as f:
                urls = json.load(f)
            url = urls.get('orchestrator', {}).get('url_jobs', '<no_url_found>')
            method = "POST"
            method_args = {"url": url,
                           "headers": spawn_header,
                           "data": json.dumps(spawn_data)}
            text, status_code, response_header = j4j_orchestrator_request(uuidcode,
                                                                          self.log,
                                                                          method,
                                                                          method_args)
            if status_code != 202:
                self.log.warning("{} - J4J_Orchestrator Post failed. J4J_Worker Response: {} {} {}".format(uuidcode, text.strip(), status_code, response_header))
                raise Exception("{} - J4J_Worker Post failed. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
            else:
                self.log.debug("{} - Spawn successful sent to J4J_Orchestrator. Port: {}".format(uuidcode, text))
                self.port = int(text.strip().replace('"', '').replace("'", ''))
        except Exception:
            self.log.exception("{} - J4J_Orchestrator communication failed. Raise web.HTTPError to inform user. {} {}".format(uuidcode, method, self.user.authenticator.remove_secret(method_args)))
            raise Exception('A mandatory background service is not running. An administrator is informed. Sorry for the inconvenience.')

        if self.user_options.get('sendmail', False):
            self.sendmail = True
        self.db_progs_no = 0
        self.job_status = 'createjob'
        self.setup_proxys(uuidcode, urls)
        if self.user_options.get('system').upper() == 'DOCKER':
            # J4J_Orchestrator will create a docker container with the name "<uuidcode>"
            return (uuidcode, self.port)
        return (urls.get('tunnel', {}).get('hostname', '<tunnel_hostname>'), self.port)


    async def poll(self):
        uuidcode = uuid.uuid4().hex
        self.log.info("{} - Poll JupyterLab: {}".format(self._log_name.lower(), uuidcode))
        db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.id == self.orm_spawner.id).first()
        if not db_spawner:
            self.log.warning("{} - {} - Poll for Spawner that does not exist in database".format(self._log_name.lower(), uuidcode))
            return 0
        self.user.db.refresh(db_spawner)
        self.log.debug("{} - Db_spawner_state: {}".format(uuidcode, db_spawner.state))
        self.load_state(db_spawner.state)
        if self.job_status in ['running', 'createjob', 'submitunicorejob', 'waitforhostname']:
            return None
        return 0

    async def stop(self):
        if self.uuidcode_tmp:
            uuidcode = self.uuidcode_tmp
            self.uuidcode_tmp = None
        else:
            uuidcode = uuid.uuid4().hex
        self.log.info("{} - Stop JupyterLab: {}".format(self._log_name.lower(), uuidcode))
        self.progs_no = 0
        with open(self.user.authenticator.j4j_urls_paths, 'r') as f:
            urls = json.load(f)
        self.remove_proxys(uuidcode, urls)
        if self.stopped:
            self.log.debug("{} - {} Already stopped by J4J_Orchestrator or J4J_Worker".format(self._log_name.lower(), uuidcode))
            self.stopped = False
            return
        db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.id == self.orm_spawner.id).first()
        if db_spawner:
            self.user.db.refresh(db_spawner)
            self.load_state(db_spawner.state)
        db_user = self.user.db.query(orm.User).filter(orm.User.name == self.user.name).first()
        if db_user:
            self.user.db.refresh(db_user)
            self.user.encrypted_auth_state = db_user.encrypted_auth_state
        state = await self.user.get_auth_state()
        orchestrator_token = get_token(self.user.authenticator.orchestrator_token_path)
        header = {'uuidcode': uuidcode,
                  'Intern-Authorization': orchestrator_token,
                  'accesstoken': state.get('accesstoken'),
                  'refreshtoken': state.get('refreshtoken'),
                  'expire': str(state.get('expire')),
                  'escapedusername': self.user.escaped_name,
                  'servername': self._log_name.lower()}
        if state.get('login_handler') == 'jscldap':
            header['tokenurl'] = self.user.authenticator.jscldap_token_url
        elif state.get('login_handler') == 'jscworkshop':
            header['tokenurl'] = self.user.authenticator.jscworkshop_token_url
        try:
            url = urls.get('orchestrator', {}).get('url_jobs', '<no_url_found>')
            method = "DELETE"
            method_args = {"url": url,
                           "headers": header,
                           "certificate": False
                          }
            text, status_code, response_header = j4j_orchestrator_request(uuidcode,  # @UnusedVariable
                                                                          self.log,
                                                                          method,
                                                                          method_args)
            if status_code != 202:
                self.log.warning("{} - Failed J4J_Orchestrator communication: {} {}".format(header['uuidcode'], text, status_code))
                raise Exception("{} - Failed J4J_Orchestrator communication. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
        except (requests.exceptions.InvalidSchema, requests.exceptions.ConnectionError):
            self.log.exception("{} - {} - J4J_Orchestrator not running? Could not stop UNICORE Job. May still run. {} {}".format(self._log_name.lower(), uuidcode, url, self.user.authenticator.remove_secret(header)))
        except:
            self.log.exception("{} - {} - Could not stop UNICORE Job. May still run. {} {}".format(self._log_name.lower(), uuidcode, url, self.user.authenticator.remove_secret(header)))
        finally:
            new_state = {
              "job_status": None,
              "db_progs_no": -1,
              "hostname": None,
              "api_token": '',
            }
            setattr(db_spawner, 'state', new_state)
            setattr(db_spawner, 'last_activity', datetime.utcnow())
            self.user.db.commit()

    async def cancel(self, uuidcode, stopped):
        try:
            self.log.info("{} - Cancel JupyterLab: {}".format(self._log_name.lower(), uuidcode))
            if str(type(self._spawn_future)) == "<class '_asyncio.Task'>" and self._spawn_future._state in ['PENDING']:
                self.log.debug("{} - {} Spawner is pending, try to cancel".format(self._log_name.lower(), uuidcode))
                self.stopped = False
                self.uuidcode_tmp = uuidcode
                await self.user.stop(self.name)
                self._spawn_future.set_result('cancelled')
                return True
            else:
                self.log.debug("{} - {} Spawner is not pending. Stop it normally.".format(self._log_name.lower(), uuidcode))
                self.stopped = stopped
                self.uuidcode_tmp = uuidcode
                await self.user.stop(self.name)
                return True
        except:
            self.log.exception("{} - Unknown Error while cancelling Server".format(self._log_name.lower()))
            return False

    async def get_options_form(self):
        try:
            if not self.name:
                raise Exception("{} - Do not allow to start without a name".format(self._log_name.lower()))
            db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.id == self.orm_spawner.id).first()
            if db_spawner:
                self.user.db.refresh(db_spawner)
                if db_spawner.user_options:
                    self.user_options = db_spawner.user_options
                    self.log.info("{} - Start with options from first server_start for this spawner: {}".format(self._log_name.lower(), self.user_options))
                    return ""
            if not self.html_code == "":
                return self.html_code
            db_user = self.user.db.query(orm.User).filter(orm.User.name == self.user.name).first()
            if db_user:
                self.user.db.refresh(db_user)
                self.user.encrypted_auth_state = db_user.encrypted_auth_state
            state = await self.user.get_auth_state()
            user_dic = state.get('user_dic', {})
            tunnel_token = get_token(self.user.authenticator.tunnel_token_path)
            maintenance = get_maintenance(user_dic.keys(), self.user.authenticator.resources, self.nodes_path, self.user.authenticator.j4j_urls_paths, tunnel_token)
            if len(maintenance) > 0:
                self.log.info("{} - Systems in Maintenance: {}".format(self._log_name.lower(), maintenance))
            reservations_var = reservations(user_dic, self.reservation_paths)
            self.html_code = create_html(user_dic, reservations_var, self.user.authenticator.resources, self.style_path, self.dockerimages_path, self.project_checkbox_path, maintenance)
        except Exception:
            self.log.exception("Could not build html page")
            #self.log.exception("{} - Could not build html page".format(self._log_name.lower()))
        return self.html_code
