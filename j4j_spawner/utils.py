import os
import json
import requests

from contextlib import closing

from .file_loads import get_token
import base64

def create_spawn_header(uuidcode, expire, refreshtoken, jhubtoken, accesstoken, account, project, servername, escapedusername, orchestrator_token_path, login_handler):
    spawn_header = {
        "uuidcode": uuidcode,
        "Intern-Authorization": get_token(orchestrator_token_path),
        "expire": str(expire),
        "refreshtoken": refreshtoken,
        "jhubtoken": jhubtoken,
        "accesstoken": accesstoken,
        "account": account,
        "project": project,
        "Content-Type": "application/json",
        "servername": servername,
        "escapedusername": escapedusername
        }
    if login_handler == 'jscusername':
        spawn_header['tokenurl'] = os.environ.get('JSCUSERNAME_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token')
        spawn_header['authorizeurl'] = os.environ.get('JSCUSERNAME_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as-username/oauth2-authz')
    else:
        spawn_header['tokenurl'] = os.environ.get('JSCLDAP_TOKEN_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2/token')
        spawn_header['authorizeurl'] = os.environ.get('JSCLDAP_AUTHORIZE_URL', 'https://unity-jsc.fz-juelich.de/jupyter-oauth2-as/oauth2-authz')
    return spawn_header

def create_spawn_data(servername, Environment, partition, reservation, Resources, service, dashboard, system, Checkboxes):
    spawn_data = {
        "servername": servername,
        "Environment": Environment.copy(),
        "partition": partition,
        "reservation": reservation,
        "Resources": Resources.copy(),
        "service": service,
        "dashboard": dashboard,
        "system": system,
        "Checkboxes": Checkboxes.copy()
        }
    return spawn_data

# remove not supported and not available systems
def get_maintenance(user_accs, urls_paths, tunnel_token):
    unicorepath = os.getenv('UNICORE_INFOS', '/etc/j4j/j4j_mount/j4j_common/unicore.json')
    with open(unicorepath, 'r') as f:
        systems = json.load(f)
    with open(urls_paths, 'r') as f:
        urls = json.load(f)
    available_url = urls.get('tunnel', {}).get('url_available')
    ret = {}
    maintenance = []
    for key, value in user_accs.items():
        maintenance.append(key)
        if key.upper() in systems.keys():
            for node in systems.get(key.upper(), {}).get('nodes', []):
                with closing(requests.get("{}?node={}".format(available_url, node), headers={'Intern-Authorization': tunnel_token}, verify=False)) as r:
                    if r.status_code == 200 and r.text.lower().strip().strip('"') == 'true':
                        ret[key] = value
                        maintenance.remove(key)
                        break
    return ret, maintenance

# add reservations
def reservations(data, reservation_paths, slurm_systems):
    ret = {}
    for name, path in reservation_paths.items():
        with open(path) as f:
            s = f.read()
        if name.upper() in slurm_systems:
            ret[name] = slurm_reservation(name.upper(), s, data)
    return ret

# reservation strings to dic
def slurm_reservation(name, s, data):
    li = s.split("ReservationName=")
    dic = {}
    ret = {'Account': {}, 'Project': {}}
    for reservation in li[1:]:
        try:
            lines = reservation.replace("\n", " ")
            lineList = lines.split()
            dic[lineList[0]] = {}
            for pair in lineList[1:]:
                keyValue = pair.split("=")
                try:
                    dic[lineList[0]][keyValue[0]] = keyValue[1]
                except IndexError:
                    dic[lineList[0]][keyValue[0]] = "unknown"
        except:
            del dic[lineList[0]]
            continue
    if name in data.keys():
        for account in data.get(name).keys():
            for reservation, infos in dic.items():
                if account in infos.get('Users'):
                    if account not in ret['Account'].keys():
                        ret['Account'][account] = {}
                    ret['Account'][account][reservation] = infos
            for project in data.get(name).get(account).keys():
                for reservation, infos in dic.items():
                    if project in infos.get('Accounts'):
                        if project not in ret['Project'].keys():
                            ret['Project'][project] = {}
                        ret['Project'][project][reservation] = infos
    return ret

def get_unity():
    with open('/etc/j4j/j4j_mount/j4j_common/unity.json', 'r') as f:
        unity = json.load(f)
    return unity

def get_accesstoken(logger, token_url, authorize_url):
    unity = get_unity()
    tokeninfo_url = unity[token_url].get('links', {}).get('tokeninfo')
    refreshtoken = unity[token_url].get('immune_tokens', [''])[0]
    cert_path = unity[token_url].get('certificate', False)
    scope = ' '.join(unity[authorize_url].get('scope'))
    b64key = base64.b64encode(bytes('{}:{}'.format(unity[token_url].get('client_id'), unity[token_url].get('client_secret')), 'utf-8')).decode('utf-8')
    data = {'refresh_token': refreshtoken,
            'grant_type': 'refresh_token',
            'scope': scope}
    headers = {'Authorization': 'Basic {}'.format(b64key),
               'Accept': 'application/json'}
    logger.debug("Unity Call: {} {} {} {}".format(token_url, headers, data, cert_path))
    with closing(requests.post(token_url,
                               headers = headers,
                               data = data,
                               verify = cert_path,
                               timeout = 1800)) as r:
        try:
            accesstoken = r.json()['access_token']
        except:
            logger.exception("Unity Response: {} {} {}".format(r.status_code, r.text, r.headers))
            raise Exception("Could not get access token")
    logger.debug("Unity Call 2: {} {} {}".format(tokeninfo_url, { 'Authorization': 'Bearer {}'.format(accesstoken) }, cert_path))
    with closing(requests.get(tokeninfo_url,
                              headers = { 'Authorization': 'Bearer {}'.format(accesstoken) },
                              verify = cert_path,
                              timeout = 1800)) as r:
        try:        
            expire = r.json()['exp']
        except:
            logger.exception("Unity Response 2: {} {} {}".format(r.status_code, r.text, r.headers))
            raise Exception("Could not get expire info")
    return accesstoken, refreshtoken, expire

