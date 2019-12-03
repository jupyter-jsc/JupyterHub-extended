import json
import os
import requests

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

from .file_loads import get_token

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
    if login_handler == 'jscldap':
        spawn_header['tokenurl'] = os.environ.get('JSCLDAP_TOKEN_URL', '')
        spawn_header['tokeninfourl'] = os.environ.get('JSCLDAP_TOKENINFO_URL', '')
        spawn_header['certpath'] = os.environ.get('JSCLDAP_CERT_PATH', '')
        spawn_header['scope'] = os.environ.get('JSCLDAP_SCOPE', '')
    elif login_handler == 'jscworkshop':
        spawn_header['tokenurl'] = os.environ.get('JSCWORKSHOP_TOKEN_URL', '')
        spawn_header['tokeninfourl'] = os.environ.get('JSCWORKSHOP_TOKENINFO_URL', '')
        spawn_header['certpath'] = os.environ.get('JSCWORKSHOP_CERT_PATH', '')
        spawn_header['scope'] = os.environ.get('JSCWORKSHOP_SCOPE', '')
    else:
        spawn_header['tokenurl'] = ''
        spawn_header['tokeninfourl'] = ''
        spawn_header['certpath'] = ''
        spawn_header['scope'] = ''
    return spawn_header

def create_spawn_data(servername, Environment, partition, reservation, Resources, system, Checkboxes):
    spawn_data = {
        "servername": servername,
        "Environment": Environment.copy(),
        "partition": partition,
        "reservation": reservation,
        "Resources": Resources.copy(),
        "system": system,
        "Checkboxes": Checkboxes.copy()
        }
    return spawn_data

# remove not supported and not available systems
def supported_systems(user_accs, nodespath, urls_paths, tunnel_token):
    with open(nodespath, 'r') as f:
        systems = json.load(f)
    with open(urls_paths, 'r') as f:
        urls = json.load(f)
    available_url = urls.get('tunnel', {}).get('url_available')
    ret = {}
    maintenance = []
    for key, value in user_accs.items():
        maintenance.append(key)
        if key.upper() in systems.keys():
            for node in systems[key.upper()]:
                with closing(requests.get("{}?node={}".format(available_url, node), headers={'Intern-Authorization': tunnel_token}, verify=False)) as r:
                    if r.status_code == 200 and r.text.lower().strip().strip('"') == 'true':
                        ret[key] = value
                        maintenance.remove(key)
                        break
    return ret, maintenance

# create dic from dispatch-entry string
def get_user_dic(hpc_infos, partitions_path, nodespath, urls_paths, tunnel_token):
    dic = {}
    for i in hpc_infos:
        infos = i.lower().split(',')
        # infos: [account, system[_partition], project, email]
        system_partition = infos[1].split('_')
        system = system_partition[0].upper()
        if not system in dic.keys():
            dic[system] = {}
        account = infos[0]
        if not account in dic.get(system).keys():
            dic[system][account] = {}
        project = infos[2]
        if not project in dic.get(system).get(account).keys():
            dic[system][account][project] = {}
        dic[system][account][project]['LoginNode'] = {}
        if len(system_partition) == 1:
            dic[system][account][project]['batch'] = {}
        elif len(system_partition) == 2:
            dic[system][account][project][system_partition[1]] = {}
    return supported_systems(fit_partition(dic, partitions_path), nodespath, urls_paths, tunnel_token)

# Remove partitions from user_account dic, which are not supported
def fit_partition(user_account, partitions_path):
    with open(partitions_path) as f:
        resources_json = json.load(f)
    ret = {}
    for system, accounts in user_account.items():
        ret[system] = {}
        for account, projects in accounts.items():
            ret[system][account] = {}
            for project, partitions in projects.items():
                ret[system][account][project] = {}
                for partition in partitions.keys():
                    if partition == "develgpus" and "gpus" not in partitions.keys():
                        continue
                    if system in resources_json.keys() and partition in resources_json.get(system):
                        ret[system][account][project][partition] = resources_json.get(system).get(partition)
    return stripper(ret)

# remove empty entries from user_account dic (except LoginNode, because there are no resources for LoginNodes)
def stripper(data):
    ret = {}
    for k, v in data.items():
        if isinstance(v, dict):
            v = stripper(v)
        #if k in ('LoginNode', 'JURECA', 'JURON', 'JUWELS') or v not in (u'', None, {}): 
        if k in ('LoginNode') or v not in (u'', None, {}): 
            ret[k] = v
    return ret

# add reservations
def reservations(data, reservation_paths):
    ret = {}
    for name, path in reservation_paths.items():
        with open(path) as f:
            s = f.read()
        if name.lower() in ['jureca', 'juwels']:
            ret[name] = juwels_jureca_reservation(name.lower(), s, data)
    return ret

# reservation strings to dic
def juwels_jureca_reservation(name, s, data):
    li = s.split("ReservationName=")
    dic = {}
    ret = {'Account': {}, 'Project': {}}
    for reservation in li[1:]:
        lines = reservation.replace("\n", " ")
        lineList = lines.split()
        dic[lineList[0]] = {}
        for pair in lineList[1:]:
            keyValue = pair.split("=")
            dic[lineList[0]][keyValue[0]] = keyValue[1]
    name = name.upper()
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
