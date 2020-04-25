import json

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
        if k in ('LoginNode', 'LoginNodeVis') or v not in (u'', None, {}):
            ret[k] = v
    return ret
