import json

# create dic from dispatch-entry string
def get_user_dic(hpc_infos, partitions_path):
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
    return fit_partition(dic, partitions_path)

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

