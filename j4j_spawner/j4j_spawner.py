'''
Created on May 17, 2019

@author: Tim Kreuzer
'''

import requests
import uuid
import json
import socket
import time
import datetime
import os

from traitlets import Unicode, Dict, List
from asyncio import sleep
from contextlib import closing

from async_generator import async_generator, yield_

from jupyterhub.spawner import Spawner
from jupyterhub import orm
from jupyterhub.utils import url_path_join


from .utils import reservations, create_spawn_data, create_spawn_header, get_maintenance, get_accesstoken
from j4j_spawner.html_jupyterlab import create_html_jupyterlab
from j4j_spawner.html_dashboard import create_html_dashboard
from .communication import j4j_orchestrator_request
from .file_loads import get_token

class J4J_Spawner(Spawner):
    # Variables for the options_form
    #partitions_path = Unicode(config=True, help='')
    reservation_paths = Dict(config=True, help='')
    cronjobinfopath = Unicode(os.environ.get('CRONJOBINFO_PATH', ''), config=True, help='')
    spawn_config_path = Unicode(config=True, help='')
    dashboards_path = Unicode(config=True, help='')
    project_checkbox_path = Unicode(config=True, help='')
    slurm_systems = List(config=True, help='', default_value=[])
    html_code = ""

    # Variables for the jupyter application
    job_status = None
    progs_messages_all = [
                      {"progress": 20, "html_message": "Creating a <a href=\"https://www.unicore.eu\">UNICORE</a> Job." },
                      {"progress": 40, "html_message": "Submitting Job to <a href=\"https://www.unicore.eu\">UNICORE</a>." },
                      {"progress": 60, "html_message": "Waiting until your <system>-Job is started. (Timeout at <timeout>)" },
                      {"progress": 80, "html_message": "Load modules on HPC System. Waiting for an answer of your Service. (Timeout at <timeout>)"}
                     ]
    progs_no = 0
    db_progs_no = -1
    hostname = None
    stopped = False
    uuidcode_tmp = None
    sendmail = False
    login_handler = ''
    useraccs_complete = False
    error_message = ""
    start_uuid = ""
    service = ""
    dashboard = ""
    system = ""
    project = ""
    account = ""
    partition = ""
    resources = ""
    reservation = ""
    starttimesec = 0
    http_timeout = 300

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
        self.useraccs_complete = False
        self.starttimesec = 0
        self.http_timeout = 300

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
            self.useraccs_complete = state.get('useraccs_complete', False)
            self.start_uuid = state.get('start_uuid', '')
            self.service = state.get('service', "")
            self.dashboard = state.get('dashboard', "")
            self.system = state.get('system', "")
            self.project = state.get('project', "")
            self.account = state.get('account', "")
            self.partition = state.get('partition', "")
            self.resources = state.get('resources', "")
            self.reservation = state.get('reservation', "")
            self.starttimesec = state.get('starttimesec', "")
            self.http_timeout = state.get('http_timeout', "")
        else:
            self.job_status = None
            self.db_progs_no = -1
            self.hostname = None
            self.api_token = ''
            self.sendmail = False
            self.login_handler = ''
            self.useraccs_complete = False
            self.start_uuid = ""
            self.service = ""
            self.dashboard = ""
            self.system = ""
            self.project = ""
            self.account = ""
            self.partition = ""
            self.resources = ""
            self.reservation = ""
            self.starttimesec = 0
            self.http_timeout = 300

    def get_state(self):
        """get the current state"""
        state = super(J4J_Spawner, self).get_state()
        state['job_status'] = self.job_status
        state['db_progs_no'] = self.db_progs_no
        state['hostname'] = self.hostname
        state['api_token'] = self.api_token
        state['sendmail'] = self.sendmail
        state['loginhandler'] = self.login_handler
        state['useraccs_complete'] = self.useraccs_complete
        state['start_uuid'] = self.start_uuid
        state['service'] = self.service
        state['dashboard'] = self.dashboard
        state['system'] = self.system
        state['project'] = self.project
        state['account'] = self.account
        state['partition'] = self.partition
        state['resources'] = self.resources
        state['reservation'] = self.reservation
        state['starttimesec'] = self.starttimesec
        state['http_timeout'] = self.http_timeout
        return state

    @property
    def started(self):
        return self.orm_spawner.started

    @async_generator
    async def progress(self):
        while self.progs_no < 4:
            db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.name == self.name).filter(orm.Spawner.user_id == self.user.orm_user.id).first()
            if not db_spawner:
                self.log.debug("userserver={} - servername={} not found.".format(self._log_name.lower(), self.name))
                return
            self.user.db.refresh(db_spawner)
            self.load_state(db_spawner.state)
            if db_spawner.user_options.get('system', 'none').lower() == 'docker' or db_spawner.user_options.get('system', 'none') == "HDF-Cloud":
                if 'starttimesec' in db_spawner.state:
                    timeout = db_spawner.state['starttimesec'] + self.http_timeout
                await yield_({'progress': 50, 'html_message': 'Start Service in a virtual Machine. (Timeout at {})'.format(datetime.datetime.fromtimestamp(timeout).strftime("%Y-%m-%d %H:%M:%S"))})
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
                if '<timeout>' in s['html_message']:
                    if 'starttimesec' in db_spawner.state:
                        timeout = db_spawner.state['starttimesec'] + self.http_timeout
                        s['html_message'] = s['html_message'].replace('<timeout>', datetime.datetime.fromtimestamp(timeout).strftime("%Y-%m-%d %H:%M:%S"))
                await yield_(s)
                self.progs_no += 1
            db_spawner = None
            await sleep(1)
        
    def setup_proxys(self, uuidcode, urls=None):
        # add routes to proxy
        if not self.user.authenticator.multiple_instances:
            self.log.debug("uuidcode={} - Do not setup proxys. Running in single instance mode.".format(uuidcode))
            return
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
            proxy_urls.append('/api/routes{baseurl}api/uxnotification/{username}/{suidlen}_{suid}_{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, suidlen=len(self.start_uuid), suid=self.start_uuid, servername=self.name))
            
            proxy_json = { 'target': target }
            if self.service == "Dashboard":
                self.log.debug("{} - Route everything but /voila to an error page / non existent page".format(uuidcode))
                proxy_urls_deny = []
                proxy_urls_deny.append('/api/routes{shortbaseurl}user/{username}/{servername}/tree'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=self.user.escaped_name, servername=self.name))
                proxy_urls_deny.append('/api/routes{shortbaseurl}user/{username}/{servername}/lab'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=self.user.escaped_name, servername=self.name))
                for proxy_url in proxy_urls_deny:
                    with closing(requests.post(proxy_base_url+proxy_url, headers=proxy_headers, json={ 'target': "http://permission_denied:8081" }, verify=False)) as r:
                        if r.status_code != 201:
                            raise Exception('{} {} {}'.format(proxy_base_url+proxy_url, r.status_code, r.text))
            for proxy_url in proxy_urls:
                with closing(requests.post(proxy_base_url+proxy_url, headers=proxy_headers, json=proxy_json, verify=False)) as r:
                    if r.status_code != 201:
                        raise Exception('{} {} {}'.format(proxy_base_url+proxy_url, r.status_code, r.text))
                self.log.debug("userserver={} - uuidcode={} Added route to proxy: {} => {}".format(self._log_name.lower(), uuidcode, proxy_url, target))
        except:
            self.log.exception("userserver={} - uuidcode={} Could not add route to proxy".format(self._log_name.lower(), uuidcode))

    def remove_proxys(self, uuidcode, urls=None):
        # delete route from proxy
        self.log.debug("userserver={} - uuidcode={} - Remove all proxy routes".format(self._log_name.lower(), uuidcode))
        db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.id == self.orm_spawner.id).first()
        self.load_state(db_spawner.state)
        proxy_urls = []
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
            proxy_urls.append('/api/routes{baseurl}api/uxnotification/{username}/{suidlen}_{suid}_{servername}'.format(baseurl=self.hub.base_url, username=self.user.escaped_name, suidlen=len(self.start_uuid), suid=self.start_uuid, servername=self.name))
            # voila urls
            proxy_urls.append('/api/routes{shortbaseurl}{username}/{servername}/dashboard'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=self.user.escaped_name, servername=self.name))
            with open(self.user.authenticator.proxy_secret, 'r') as f:
                proxy_secret = f.read().strip()
            proxy_secret = proxy_secret.strip()[len('export CONFIGPROXY_AUTH_TOKEN='):]
            proxy_headers = {'Authorization': 'token {}'.format(proxy_secret)}
            if self.service == "Dashboard":
                self.log.debug("{} - Route everything but /voila to an error page / non existent page".format(uuidcode))
                proxy_urls.append('/api/routes{shortbaseurl}user/{username}/{servername}/tree'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=self.user.escaped_name, servername=self.name))
                proxy_urls.append('/api/routes{shortbaseurl}user/{username}/{servername}/lab'.format(shortbaseurl=self.hub.base_url[:-len('hub/')], username=self.user.escaped_name, servername=self.name))
            for proxy_url in proxy_urls:
                try:
                    with closing(requests.delete(proxy_base_url+proxy_url, headers=proxy_headers, verify=False)) as r:
                        if r.status_code != 204 and r.status_code != 404:
                            raise Exception('{} {}'.format(r.status_code, r.text))
                    self.log.debug("userserver={} - uuidcode={} Delete route from proxy: {}".format(self._log_name.lower(), uuidcode, proxy_url))
                except:
                    self.log.exception("userserver={} - uuidcode={} Could not delete route {} from proxy".format(self._log_name.lower(), uuidcode, proxy_url))
        except:
            self.log.exception("userserver={} - uuidcode={} Could not delete route from proxy".format(self._log_name.lower(), uuidcode))

    async def start(self):
        if 'system' not in self.user_options:
            # This errors occures, if you are able to trigger this function, without having your uids loaded first (Example: Open Home, load users, restart Hub, press Spawn)
            raise Exception("Not allowed")
        if ':' not in self._log_name.lower():
            raise Exception("Not allowed")

        # Create uuidcode to track this specific Call through the webservices
        uuidcode = uuid.uuid4().hex
        self.start_uuid = uuidcode
        self.log.info("userserver={}, uuidcode={}, username={}, action=start, system={}, account={}, sendmail={}, project={}, partition={}, reservation={}, checkboxes={}, resources={}".format(self._log_name.lower(), uuidcode, self.user.name, self.user_options.get('system', ''), self.user_options.get('account', ''), self.user_options.get('sendmail', False), self.user_options.get('project', ''), self.user_options.get('partition', ''), self.user_options.get('reservation', ''), self.user_options.get('Checkboxes', []), self.user_options.get('Resources', {})))
        # get a few JupyterHub variables, which we will need to create spawn_header and spawn_data
        db_user = self.user.db.query(orm.User).filter(orm.User.name == self.user.name).first()
        if db_user:
            self.user.db.refresh(db_user)
            self.user.encrypted_auth_state = db_user.encrypted_auth_state
        state = await self.user.get_auth_state()
        if len(state.get('accesstoken', 0)) == 0 or len(state.get('refreshtoken', 0)) == 0 or len(state.get('expire', 0)) == 0:
                    # check for cron job:
            try:
                with open(self.cronjobinfopath, 'r') as f:
                    cron_job = json.load(f)
                if self.user.name == cron_job.get('username', '') and \
                cron_job.get('systems', {}).get(self.user_options.get('system', '').upper(), {}).get('servername', '') == self._log_name.lower().split(':')[1] and \
                cron_job.get('systems', {}).get(self.user_options.get('system', '').upper(), {}).get('account', '') == self.user_options.get('account', '') and \
                cron_job.get('systems', {}).get(self.user_options.get('system', '').upper(), {}).get('project', '') == self.user_options.get('project', '') and \
                cron_job.get('systems', {}).get(self.user_options.get('system', '').upper(), {}).get('partition', '') == self.user_options.get('partition', ''):
                    accesstoken, refreshtoken, expire = get_accesstoken(self.log, cron_job.get('tokenurl', ''), cron_job.get('authorizeurl', ''))
                    state['accesstoken'] = accesstoken
                    state['expire'] = expire
                    state['refreshtoken'] = refreshtoken
                    state['loginhandler'] = "jscldap"
                    await self.user.save_auth_state(state)
                else:
                    self.handler.redirect(self.user.authenticator.logout_url(self.hub.base_url))
                    raise Exception("{} - Could not find auth state. Please login again.".format(uuidcode))
            except:
                self.log.exception("Could not check for cron job infos")
                self.handler.redirect(self.user.authenticator.logout_url(self.hub.base_url))
                raise Exception("{} - Could not find auth state. Please login again.".format(uuidcode))
        self.service = self.user_options.get('service', '')
        self.dashboard = self.user_options.get('dashboard', '')
        self.system = self.user_options.get('system', '')
        self.project = self.user_options.get('project', '')
        self.account = self.user_options.get('account', '')
        self.partition = self.user_options.get('partition', '')
        self.resources =  ' '.join(["{}: {}".format(k,v) if k != "Runtime" else "{}: {}".format(k,int(v/60)) for k,v in self.user_options.get('Resources', {}).items()])
        self.reservation = self.user_options.get('reservation')
        self.starttimesec = int(time.time())
        # set http_timeout
        if self.system == 'HDF-Cloud' or self.user_options.get('partition', 'LoginNode') in ['LoginNode', 'LoginNodeVis']:
            self.http_timeout = 300
        else:
            self.http_timeout = 12*60*60
        self.log.debug("uuidcode={} Set http_timeout to {}".format(uuidcode, self.http_timeout))

        env = self.get_env()
        self.log.debug("uuidcode={} - Environment: {}".format(uuidcode, env))
        if env['JUPYTERHUB_API_TOKEN'] == "":
            env = self.get_env()
            self.log.debug("uuidcode={} - Environment had no token, second try: {}".format(uuidcode, env))
            if env['JUPYTERHUB_API_TOKEN'] == "":
                self.log.debug("uuidcode={} - Still nothing. Try to do it manually".format(uuidcode))
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
                    self.log.debug("uuidcode={} - New Environment: {}".format(uuidcode, env))
                except:
                    self.log.exception("uuidcode={} - Could not create own environment".format(uuidcode))
                    raise Exception("uuidcode={} - Could not load environment. Please try again".format(uuidcode))
        if self.system != 'HDF-Cloud':
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
                                           self.account,
                                           self.project,
                                           self._log_name.lower(),
                                           self.user.escaped_name,
                                           self.user.authenticator.orchestrator_token_path,
                                           state.get('login_handler', ''))
        spawn_data = create_spawn_data(self._log_name.lower(),
                                       env,
                                       self.partition,
                                       self.reservation,
                                       self.user_options.get('Resources', {}),
                                       self.service,
                                       self.dashboard,
                                       self.system,
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
                self.log.warning("uuidcode={} - J4J_Orchestrator Post failed. J4J_UNICORE Response: {} {} {}".format(uuidcode, text.strip(), status_code, response_header))
                raise Exception("uuidcode={} - J4J_UNICORE Post failed. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
            else:
                self.log.debug("uuidcode={} - Spawn successful sent to J4J_Orchestrator. Port: {}".format(uuidcode, text))
                self.port = int(text.strip().replace('"', '').replace("'", ''))
        except Exception:
            self.log.exception("uuidcode={} - J4J_Orchestrator communication failed. Raise web.HTTPError to inform user. {} {}".format(uuidcode, method, self.user.authenticator.remove_secret(method_args)))
            raise Exception('A mandatory background service is not running. An administrator is informed. Sorry for the inconvenience.')

        if 'sendmail' in self.user_options.get('Checkboxes', {}).keys():
            self.sendmail = True
        self.db_progs_no = 0
        self.job_status = 'createjob'
        self.setup_proxys(uuidcode, urls)
        #if self.user_options.get('system').upper() == 'DOCKER':
        #   # J4J_Orchestrator will create a docker container with the name "<uuidcode>"
        #    return (uuidcode, self.port)
        return (urls.get('tunnel', {}).get('hostname', '<tunnel_hostname>'), self.port)


    async def poll(self):
        uuidcode = uuid.uuid4().hex
        self.log.info("userserver={}, action=poll, username={}, uuidcode={}".format(self._log_name.lower(), self.user.name, uuidcode))
        db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.id == self.orm_spawner.id).first()
        if not db_spawner:
            self.log.warning("userserver={} - uuidcode={} - Poll for Spawner that does not exist in database".format(self._log_name.lower(), uuidcode))
            return 0
        self.user.db.refresh(db_spawner)
        #self.log.debug("{} - Db_spawner_state: {}".format(uuidcode, db_spawner.state))
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
        self.log.info("userserver={}, action=stop, username={}, uuidcode={}".format(self._log_name.lower(), self.user.name, uuidcode))
        self.progs_no = 0
        with open(self.user.authenticator.j4j_urls_paths, 'r') as f:
            urls = json.load(f)
        self.remove_proxys(uuidcode, urls)
        if self.stopped:
            self.log.debug("userserver={} - uuidcode={} Already stopped by J4J_Orchestrator or J4J_UNICORE".format(self._log_name.lower(), uuidcode))
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
            header['authorizeurl'] = self.user.authenticator.jscldap_authorize_url
        elif state.get('login_handler') == 'jscusername':
            header['tokenurl'] = self.user.authenticator.jscusername_token_url
            header['authorizeurl'] = self.user.authenticator.jscusername_authorize_url
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
                self.log.warning("uuidcode={} - Failed J4J_Orchestrator communication: {} {}".format(header['uuidcode'], text, status_code))
                raise Exception("uuidcode={} - Failed J4J_Orchestrator communication. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
        except (requests.exceptions.InvalidSchema, requests.exceptions.ConnectionError):
            self.log.exception("userserver={} - uuidcode={} - J4J_Orchestrator not running? Could not stop UNICORE Job. May still run. {} {}".format(self._log_name.lower(), uuidcode, url, self.user.authenticator.remove_secret(header)))
        except:
            self.log.exception("userserver={} - uuidcode={} - Could not stop UNICORE Job. May still run. {} {}".format(self._log_name.lower(), uuidcode, url, self.user.authenticator.remove_secret(header)))
        finally:
            new_state = {
              "job_status": None,
              "db_progs_no": -1,
              "hostname": None,
              "api_token": ''
            }
            setattr(db_spawner, 'state', new_state)
            setattr(db_spawner, 'last_activity', datetime.datetime.utcnow())
            self.user.db.commit()

    async def cancel(self, uuidcode, stopped):
        try:
            self.log.info("userserver={}, action=cancel, username={}, uuidcode={}".format(self._log_name.lower(), self.user.name, uuidcode))
            if str(type(self._spawn_future)) == "<class '_asyncio.Task'>" and self._spawn_future._state in ['PENDING']:
                self.log.debug("userserver={} - uuidcode={} Spawner is pending, try to cancel".format(self._log_name.lower(), uuidcode))
                self.stopped = False
                self.uuidcode_tmp = uuidcode
                await self.user.stop(self.name)
                self._spawn_future.set_result('cancelled')
                return True
            else:
                self.log.debug("userserver={} - uuidcode={} Spawner is not pending. Stop it normally.".format(self._log_name.lower(), uuidcode))
                self.stopped = stopped
                self.uuidcode_tmp = uuidcode
                await self.user.stop(self.name)
                return True
        except:
            self.log.exception("userserver={} - Unknown Error while cancelling Server".format(self._log_name.lower()))
            return False

    async def get_options_form(self):
        try:
            #if not self.name:
            #    raise Exception("{} - Do not allow to start without a name".format(self._log_name.lower()))
            db_spawner = self.user.db.query(orm.Spawner).filter(orm.Spawner.id == self.orm_spawner.id).first()
            self.load_state(db_spawner.state)
            if db_spawner:
                self.user.db.refresh(db_spawner)
                if db_spawner.user_options:
                    self.user_options = db_spawner.user_options
                    self.log.debug("userserver={} - Start with options from first server_start for this spawner: {}".format(self._log_name.lower(), self.user_options))
                    return ""
            # since we update the hpc_infos external we have to build it, even if it was build for this spawner already
            #if not self.html_code == "":
            #    if self.useraccs_complete:
            #        return self.html_code
            db_user = self.user.db.query(orm.User).filter(orm.User.name == self.user.name).first()
            if db_user:
                self.user.db.refresh(db_user)
                self.user.encrypted_auth_state = db_user.encrypted_auth_state
            state = await self.user.get_auth_state()
            # since we update the hpc_infos external we have to build it, even if it was build for this spawner already
            #if state.get('useraccs_complete', False) == self.useraccs_complete and not self.html_code == "": 
            #    return self.html_code
            user_dic = state.get('user_dic', {})
            self.useraccs_complete = state.get('useraccs_complete', False)
            # save state in db
            setattr(db_spawner, 'state', self.get_state())
            self.user.db.commit()
            tunnel_token = get_token(self.user.authenticator.tunnel_token_path)
            user_dic, maintenance = get_maintenance(user_dic, self.user.authenticator.j4j_urls_paths, tunnel_token)
            if len(maintenance) > 0:
                self.log.debug("userserver={} - Systems in Maintenance: {}".format(self._log_name.lower(), maintenance))
            reservations_var = reservations(user_dic, self.reservation_paths, self.slurm_systems)
            #if self.user.name in self.user.authenticator.admin_users:
            #    self.log.debug("User_dic: {}".format(user_dic))
            #    self.log.debug("Reservations_paths: {}".format(self.reservation_paths))
            #    self.log.debug("slurm_systems: {}".format(self.slurm_systems))
            #    self.log.debug("Reservations_var: {}".format(reservations_var))
            with open(self.spawn_config_path, 'r') as f:
                spawn_config = json.load(f)
            with open(self.user.authenticator.unicore_infos, 'r') as f:
                ux = json.load(f)
            user_dic['HDF-Cloud'] = ux.get('HDFCLOUD', {}).get('images')
            with open(self.dashboards_path, 'r') as f:
                dashboards = json.load(f)
            with open(self.project_checkbox_path, 'r') as f:
                checkboxes = json.load(f)
            self.service = state.get('spawner_service', {}).get(self.name, 'JupyterLab')
            if state.get('spawner_service', {}).get(self.name, 'JupyterLab') == 'JupyterLab':
                self.html_code = create_html_jupyterlab(spawn_config.get('jupyterlab_sorted', []),                                                        
                                                        user_dic,
                                                        reservations_var,
                                                        checkboxes,
                                                        maintenance,
                                                        ux,
                                                        spawn_config.get('overallText', {}))              
            elif state.get('spawner_service', {}).get(self.name, 'Dashboard') == 'Dashboard':
                self.html_code = create_html_dashboard(spawn_config.get('dashboard_sorted', []),
                                                       user_dic,
                                                       dashboards,
                                                       reservations_var,
                                                       checkboxes,
                                                       maintenance,
                                                       ux,
                                                       spawn_config.get('overallText'))
        except Exception:
            self.log.exception("Could not build html page")
        return self.html_code


    def options_from_form(self, form_data):
        ret = {}
        self.log.info("Form_data: {}".format(form_data))
        """
        d = {'first_input': ['JupyterLab'],
             'dashboard_input': ['undefined'],
             'second_input': ['JUWELS'],
             'third_input': ['kreuzer1'],
             'fourth_input': ['ccstvs'],
             'fifth_input': ['gpus'],
             'sixth_input': ['undefined'],
             'resource_nodes_name': ['1'],
             'resource_runtime_name': ['60'],
             'resource_gpus_name': ['4'],
             'resource_cpus_per_node_name': ['24']}
        
        d = {'first_input': ['JupyterLab'],
             'dashboard_input': ['undefined'],
             'second_input': ['JURECA'],
             'third_input': ['kreuzer1'],
             'fourth_input': ['training1911'],
             'fifth_input': ['gpus'],
             'sixth_input': ['rs-img-proc-gpu-2'],
             'JupyterLab_ALL_ALL_ALL_ALL_sendmail_name': ['on'],
             'resource_nodes_name': ['1'],
             'resource_runtime_name': ['60'],
             'resource_gpus_name': ['4'],
             'resource_cpus_per_node_name': ['24']}
        """        
        with open(self.project_checkbox_path, 'r') as f:
            checkboxes = json.load(f)
        with open(self.user.authenticator.resources, 'r') as f:
            filled_resources = json.load(f)
        ret['service'] = form_data.get('first_input')[0]
        ret['dashboard'] = form_data.get('dashboard_input')[0]
        ret['system'] = form_data.get('second_input')[0]
        ret['account'] = form_data.get('third_input')[0]
        ret['project'] = form_data.get('fourth_input')[0]
        ret['partition'] = form_data.get('fifth_input')[0]
        ret['reservation'] = form_data.get('sixth_input')[0]
        if ret['reservation'] == "undefined":
            ret['reservation'] = None
        ret['Checkboxes'] = {}
        for service in [ret['service'], "ALL"]:
            for system in [ret['system'], "ALL"]: 
                for account in [ret['account'], "ALL"]:
                    for project in [ret["project"], "ALL"]:
                        for partition in [ret["partition"], "ALL"]:
                            for cbname, cb_infos in checkboxes.get(service, {}).get(system, {}).get(account, {}).get(project, {}).get(partition, {}).items():
                                if '{}_{}_{}_{}_{}_{}_name'.format(service, system, account, project, partition, cbname) in form_data.keys():
                                    ret['Checkboxes'][cbname] = cb_infos
        if ret['system'] == 'HDF-Cloud':
            return ret
        # -- 1 --            
        if ret['partition'] in ['LoginNode', 'LoginNodeVis']:
            return ret
        # Resources
        ret['Resources'] = {}
        for res_name, res_infos in filled_resources.get(ret['system'], {}).get(ret['partition'], {}).items():
            s = 'resource_{}_name'.format(res_name.lower())
            ret['Resources'][res_name] = int(form_data[s][0])*res_infos.get('DIVISOR', 1)
        return ret