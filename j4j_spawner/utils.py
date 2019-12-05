import os
import json
import requests

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
    elif login_handler == 'jscworkshop':
        spawn_header['tokenurl'] = os.environ.get('JSCWORKSHOP_TOKEN_URL', '')
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
def get_maintenance(user_accs_keys, nodespath, urls_paths, tunnel_token):
    with open(nodespath, 'r') as f:
        systems = json.load(f)
    with open(urls_paths, 'r') as f:
        urls = json.load(f)
    available_url = urls.get('tunnel', {}).get('url_available')
    maintenance = []
    for key in user_accs_keys:
        maintenance.append(key)
        if key.upper() in systems.keys():
            for node in systems[key.upper()]:
                with closing(requests.get("{}?node={}".format(available_url, node), headers={'Intern-Authorization': tunnel_token}, verify=False)) as r:
                    if r.status_code == 200 and r.text.lower().strip().strip('"') == 'true':
                        maintenance.remove(key)
                        break
    return maintenance

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




