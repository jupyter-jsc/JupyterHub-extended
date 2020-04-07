'''
Created on May 17, 2019

@author: Tim Kreuzer
'''

import json

colon = '--colon--' # replace : with --colon-- in variable names
slash = '--slash--' # "
dot = '--dot--'     # "

def create_html(user_accs, reservations, partitions_path, stylepath, dockerimagespath, project_checkbox_path, maintenance, useraccs_complete):
    with open(partitions_path) as f:
        resources_json = json.load(f)
    with open(project_checkbox_path) as f:
        project_checkbox = json.load(f)
    html = '\n'
    if len(maintenance) > 0:
        html += '<h3 class="maintenance_j4j">The following systems are not available right now: {}</h3>\n'.format(', '.join(maintenance))
    script = '\n'
    # default values
    user_accs_w_docker = []
    disclaimer = {}
    for system, accounts in user_accs.items():
        if "!!DISCLAIMER!!" in accounts.keys():
            disclaimer[system] = True
            del accounts["!!DISCLAIMER!!"]            
    for key in sorted(user_accs.keys()):
        user_accs_w_docker.append(key)
    if len(dockerimagespath) > 0:
        user_accs_w_docker.append('Docker')
    with open(dockerimagespath, 'r') as f:
        dockerimages_wn = f.readlines()
    dockerimages = [line.rstrip('\n') for line in dockerimages_wn]
    docker_show = False
    if len(user_accs) > 0:
        system = sorted(user_accs.keys(), key=lambda s: s.casefold())[0]
        account = sorted(user_accs.get(system).keys(), key=lambda s: s.casefold())[0]
        project = sorted(user_accs.get(system).get(account).keys(), key=lambda s: s.casefold())[0]
        partition = sorted(user_accs.get(system).get(account).get(project).keys())[0]
        reservation_default = 'None'
    else:
        system = "Docker"
        account = dockerimages[0]
        project = 'None'
        partition = 'None'
        reservation_default = 'None'
        docker_show = True
    html += inputs(system, account, project, partition, reservation_default)
    html += '<div class="j4j">\n'
    script += function_hide_all(user_accs, reservations)
    html += '  <div id="system___div" style="display:display">\n'
    if not useraccs_complete:
        html += '<center><h4>We"re looking for your accounts in the background.<br>If you"re missing accounts please refresh the page after a few seconds.</h4></center>'
    t1, t2 = dropdown(user_accs_w_docker, 'System:', 'system')
    html += t1
    html += '  </div>\n'
    script += t2
    for system, accounts in user_accs.items():
        t1, t2 = html_system('system___'+system, accounts, resources_json.get(system, {}), reservations.get(system, {}), project_checkbox, disclaimer.get(system, False), system==sorted(user_accs.keys(), key=lambda s: s.casefold())[0])
        html += t1
        script += t2
    t1, t2 = docker('system___Docker', dockerimages, docker_show, project_checkbox)
    html += t1
    script += t2
    html += '</div>\n'
    style  = '\n'
    style += '<style>\n'
    with open(stylepath) as f:
        l = f.read()
    style += l
    style += '</style>\n'
    return style+''+html+'\n<script>'+script+'\n</script>\n'


def docker(system, dockerimages, docker_show, project_checkbox):
    html = ''
    script = ''
    if docker_show:
        html += '  <div id="{div_id}___div" style="display:display">\n'.format(div_id=system)
    else:
        html += '  <div id="{div_id}___div" style="display:none">\n'.format(div_id=system)
    t1, t2 = docker_dropdown(dockerimages, "Docker Image:", system)
    html += t1
    script += t2
    for project_cb_name, project_cb in project_checkbox.get('DOCKER', {}).items():
        t1, t2 = checkbox(system+'___'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
        html += t1
        script += t2
    for project_cb_name, project_cb in project_checkbox.get('ALL', {}).items():
        if project_cb.get('docker', 'false').lower() == 'true':
            t1, t2 = checkbox(system+'___'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
            html += t1
            script += t2
    html += '    <font size="+1">For more information look at this <a href="https://nbviewer.jupyter.org/github/kreuzert/Jupyter-JSC/blob/master/FAQ.ipynb" target="_blank">FAQ</a></font><br>\n'
    html += '    <font size="+1">Overview of installed <a href="https://nbviewer.jupyter.org/github/kreuzert/Jupyter-JSC/blob/master/Extensions.ipynb" target="_blank">extensions</a></font>\n'
    html += '  </div>\n'
    return html, script


# create 5 inputs for the dropdown menus
def inputs(system, account, project, partition, reservation, show=False):
    ret = ''
    ret += '<input autocomplete="off" id="system_input" name="system_input" value="'+system+'" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="account_input" name="account_input" value="'+account+'" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="project_input" name="project_input" value="'+project+'" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="partition_input" name="partition_input" value="'+partition+'" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="reservation_input" name="reservation_input" value="'+reservation+'" style="display:'+('display' if show else 'none')+'">\n'
    return ret

# jquery function: hide every div
def function_hide_all(user_accs, reservations):
    script = 'function hideAll(){\n'
    for sys, dic in user_accs.items():
        script += "  $('#system___{}___div').hide();\n".format(sys)
        if len(dic) == 0:
            continue
        for account, projects in dic.items():
            script += "  $('#system___{}___{}___div').hide();\n".format(sys, account)
            if len(projects) == 0:
                continue
            for project, partitions in projects.items():
                script += "  $('#system___{}___{}___{}___div').hide();\n".format(sys, account, project)
                if len(partitions) == 0:
                    continue
                for partition in partitions.keys():
                    script += "  $('#system___{}___{}___{}___{}___div').hide();\n".format(sys, account, project, partition)
                    script += "  $('#system___{}___{}___{}___{}___reservation_input').prop('checked', false);\n".format(sys, account, project, partition)
                    reservation_already_used = []
                    reservations_length = 0
                    for reservation_name, infos in reservations.get(sys, {}).get('Account', {}).get(account, {}).items():
                        if partition in infos.get('PartitionName'):
                            script += "  $('#system___{}___{}___{}___{}___reservation___{}___div').hide();\n".format(sys, account, project, partition, reservation_name)
                            reservation_already_used.append(reservation_name)
                            reservations_length += 1
                    for reservation_name, infos in reservations.get(sys, {}).get('Project', {}).get(project, {}).items():
                        if partition in infos.get('PartitionName'):
                            if reservation_name not in reservation_already_used:
                                script += "  $('#system___{}___{}___{}___{}___reservation___{}___div').hide();\n".format(sys, account, project, partition, reservation_name)
                                reservations_length += 1
                    if reservations_length > 0:
                        script += "  $('#system___{}___{}___{}___{}___reservation___None___div').hide();\n".format(sys, account, project, partition)
    # hide docker stuff, too
    script += "  $('#system___{}___div').hide();\n".format('Docker')
    script += '}\n'
    return script


def html_system(system, accounts, resources_filled, reservations, project_checkbox, disclaimer, show=False):
    html  = ''
    script = ''
    t1, t2 = dropdowns(system, accounts, resources_filled, reservations, project_checkbox, disclaimer, show)
    html += t1
    script += t2
    return (html, script)

def dropdowns(system, accounts, resources_filled, reservations, project_checkbox, disclaimer, show=False):
    html  = ''
    script = ''
    system_name_list = system.split('___')
    system_name = ''
    if len(system_name_list) == 2:
        system_name = system_name_list[1].upper()
    accountlist = sorted(accounts.keys(), key=lambda s: s.casefold())
    if show:
        html += '  <div id="{div_id}___div" style="display:display">\n'.format(div_id=system)
    else:
        html += '  <div id="{div_id}___div" style="display:none">\n'.format(div_id=system)
    t1, t2 = dropdown(accountlist, 'Account:', system)
    html += t1
    script += t2
    for account, projects in accounts.items():
        projectlist = sorted(projects.keys(), key=lambda s: s.casefold())
        if account == accountlist[0]:
            html += '  <div id="{div_id}___div" style="display:display">\n'.format(div_id=system+'___'+account)
        else:
            html += '  <div id="{div_id}___div" style="display:none">\n'.format(div_id=system+'___'+account)
        t1, t2 = dropdown(projectlist, 'Project:', system+'___'+account)
        html += t1
        script += t2
        for project, partitions in projects.items():
            partitions_supported = {}
            for part in partitions.keys():
                if part in resources_filled.keys():
                    partitions_supported[part] = partitions.get(part)
            partitionlist = sorted(partitions_supported.keys())
            if len(partitionlist) == 0:
                continue
            if project==projectlist[0] and account==accountlist[0]:
                html += '  <div id="{div_id}___div" style="display:display">\n'.format(div_id=system+'___'+account+'___'+project)
            else:
                html += '  <div id="{div_id}___div" style="display:none">\n'.format(div_id=system+'___'+account+'___'+project)
            t1, t2 = dropdown(partitionlist, 'Partition:', system+'___'+account+'___'+project)
            html += t1
            script += t2
            for partition, resources in partitions_supported.items():
                if partition==partitionlist[0] and project==projectlist[0] and account==accountlist[0]:
                    html += '<div id="{}___div" style="display:display">\n'.format(system+'___'+account+'___'+project+'___'+partition)
                else:
                    html += '<div id="{}___div" style="display:none">\n'.format(system+'___'+account+'___'+project+'___'+partition)
                reservation_for_partition = {}
                for reservation_name, infos in reservations.get('Account', {}).get(account, {}).items():
                    if infos.get('PartitionName').lower() == partition:
                        reservation_for_partition[reservation_name] = infos
                for reservation_name, infos in reservations.get('Project', {}).get(project, {}).items():
                    if infos.get('PartitionName').lower() == partition and reservation_name not in reservation_for_partition.keys():
                        reservation_for_partition[reservation_name] = infos
                reservationlist = sorted(reservation_for_partition.keys())
                if len(reservationlist) > 0:
                    reservationlist.insert(0, 'None')
                    t1, t2 = dropdown(reservationlist, 'Reservation:', system+'___'+account+'___'+project+'___'+partition, reservation_for_partition)
                    html += t1
                    script += t2
                    t1, t2 = checkbox(system+'___'+account+'___'+project+'___'+partition+'___reservation', "Show reservation info", "Show more information for your reservations")
                    html += t1
                    script += t2
                    for s in reservationlist:
                        t1,t2 = reservationInfo(system+'___'+account+'___'+project+'___'+partition+'___reservation___'+s, reservation_for_partition.get(s))
                        html += t1
                for resource, infos in resources.items():
                    html += html_resource(infos, system+'___'+account+'___'+project+'___'+partition+'___'+resource)
                for project_cb_name, project_cb in project_checkbox.get(system_name, {}).items():
                    if partition in project_cb.get('partition', []):
                        t1, t2 = checkbox(system+'___'+account+'___'+project+'___'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
                        html += t1
                        script += t2
                html += '</div>\n'
                
            for project_cb_name, project_cb in project_checkbox.get(system_name, {}).items():
                if project in project_cb.get('projects', []):
                    t1, t2 = checkbox(system+'___'+account+'___'+project+'___'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
                    html += t1
                    script += t2
            html += '</div>\n'
        html += '</div>\n'
    for project_cb_name, project_cb in project_checkbox.get('ALL', {}).items():
        t1, t2 = checkbox(system+'___'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
        html += t1
        script += t2

    html += '  <p><font size="+1">Overview of installed <a href="https://nbviewer.jupyter.org/github/kreuzert/Jupyter-JSC/blob/master/Extensions.ipynb" target="_blank">extensions</a>\n'
    html += '  </font></p>'
    html += '</div>\n'
    return html, script

def reservationInfo(div_id, reservation):
    html = '<div id="{}___div" class="reservation_info_j4j" style="display: none">\n'.format(div_id)
    html += '  <table class="table_j4j">\n'
    html += '    <tr class="table_tr_j4j">\n'
    tmp = div_id.split('___')
    name = tmp[len(tmp)-1]
    html += '      <th colspan="2" class="table_th_j4j">Reservation: {}</th>\n'.format(name)
    html += '    </tr>\n'
    if '_None' == div_id[-len('_None'):]:
        html += '    <tr class="table_tr_j4j">\n'
        html += '      <td colspan="2" class="table_tdl_j4j">Please choose a reservation</td>\n'
        html += '    </tr>\n'
    else:
        reservation_sorted = sorted(reservation.keys(), key=lambda s: s.casefold())
        reservation_sorted.remove('Accounts')
        reservation_sorted.remove('Users')
        reservation_sorted.remove('StartTime')
        reservation_sorted.remove('EndTime')
        reservation_sorted.remove('State')
        reservation_sorted.insert(0, 'Users')
        reservation_sorted.insert(0, 'Accounts')
        reservation_sorted.insert(0, 'EndTime')
        reservation_sorted.insert(0, 'StartTime')
        reservation_sorted.insert(0, 'State')
        for key in reservation_sorted:
            html += '    <tr class="table_tr_j4j">\n'
            if key == 'State' and reservation.get(key) == 'INACTIVE':
                html += '      <td class="table_tdl_j4j" style="color:red; font-weight:bold">{}</td>\n'.format(key)
                html += '      <td class="table_tdr_j4j" style="color:red; font-weight:bold">{}</td>\n'.format(reservation.get(key))
            else:
                html += '      <td class="table_tdl_j4j">{}</td>\n'.format(key)
                html += '      <td class="table_tdr_j4j">{}</td>\n'.format(reservation.get(key))
            html += '    </tr>\n'
    html += '  </table>\n'
    html += '</div>\n'
    return html, ''


def checkbox(div_id, text, tooltip, noqm=False):
    html = ''
    html += '  <div id="{}" class="checkbox_div_j4j">\n'.format(div_id)
    if noqm:
        html += '    <li class="bg-primary list-group-item checkbox_li_j4j">{text}&nbsp;<img class="qm_j4j" id="{div_id}_image" src="/static/images/noqm.png" data-original-title="" title="" height="20">\n'.format(div_id=div_id, text=text)
    else:
        html += '    <li class="bg-primary list-group-item checkbox_li_j4j">{text}&nbsp;<img class="qm_j4j" id="{div_id}_image" src="/static/images/qm.png" data-original-title="" title="" height="20">\n'.format(div_id=div_id, text=text)
    html += '      <div class="material-switch pull-right" style="">\n'
    html += '        <input id="{div_id}_input" name="{div_id}_name" class="form-control" type="checkbox">\n'.format(div_id=div_id)
    html += '        <label for="{div_id}_input" class="label-primary"></label>\n'.format(div_id=div_id)
    html += '      </div>\n'
    html += '    </li>\n'
    html += '  </div>\n'
    script = ''
    if not noqm:
        script += "jQuery('#"+div_id+"_image').ready(function(e){\n"
        script += "  $('#"+div_id+"_image').tooltip({title: '"+tooltip+"', delay: 0, placement: 'bottom', html: true});\n"
        script += "});\n"
    if '___reservation' == div_id[-len('___reservation'):]:
        script += "$('#"+div_id+"_input').click(function() {\n"
        script += "  var reservation = $('#reservation_input').val();\n"
        script += "  $('#"+div_id+"___'+reservation+'___div').toggle(this.checked);\n"
        script += "});\n"
    return html, script

def html_resource(dic, div_id):
    text = dic.get('TEXT')
    mima = dic.get('MINMAX')
    mima = [str(int(float(x)/dic.get('DIVISOR', 1))) for x in mima]
    text = text.replace('_min_', str(mima[0]))
    text = text.replace('_max_', str(mima[1]))
    ret  = ''
    #ret += '  <label for="{}_input" class="bg-primary text-center">{}</label>\n'.format(div_id, text)
    ret += '  <div>\n'
    ret += '    <label for="{}_input" class="resource_label_j4j">{}</label>\n'.format(div_id, text)
    default_value = dic.get('DEFAULT')
    if default_value == '_max_':
        default_value = mima[1]
    elif default_value == '_min_':
        default_value = mima[0]
    ret += '    <input min="{}" max="{}" value="{}" class="input_j4j" name="{}_name" id="{}_input" type="number">\n'.format(mima[0], mima[1], default_value, div_id, div_id)
    ret += '  </div>\n'
    return ret

def docker_dropdown(li, text, div_id):
    html = ''
    html += '    <div class="dropdown_j4j">\n'
    html += '      <label for="{div_id}" class="bg-primary text-center label_j4j">{text}</label>\n'.format(div_id=div_id, text=text)
    html += '      <div class="btn-group btn_group_j4spawner">\n'
    html += '        <button type="button" class="btn btn-primary dropdown-toggle form-control button_j4j" data-toggle="dropdown" aria-expanded="false" id="{div_id}" name="{div_id}_name" value="{default}">\n'.format(div_id=div_id, default=li[0])
    html += '          {}\n'.format(li[0])
    html += '          <span class="caret"></span>\n'
    html += '        </button>\n'
    html += '        <ul class="dropdown-menu" name="uid" id="{}___ul">\n'.format(div_id)
    for key in li:
        html += '          <li><a href="#" id="{div_id}___element___{key}">{key_name}</a></li>\n'.format(div_id=div_id, key=key.replace('/', slash).replace(':', colon).replace('.', dot), key_name=key)
    html += '        </ul>\n'
    html += '      </div>\n'
    html += '    </div>\n'
    script  = ''
    for key in li:
        script += "jQuery('#"+div_id+"___element___"+key.replace('/', slash).replace(':', colon).replace('.', dot)+"').click(function(e){\n"
        var = 'account'
        script += "  if ( $('#"+var+"_input').val() === \""+key+"\" ){\n"
        script += "    e.preventDefault();\n"
        script += "  } else {\n"
        script += "    $('#{}').val('{}');\n".format(div_id, key)
        script += "    $('#{}').html('{} <span class=\"caret\"></span>');\n".format(div_id, key)
        script += "    $('#{}_input').val('{}');\n".format(var, key)
        script += "    hideAll();\n"
        split = div_id.split('___')
        for i in range(1,len(split)):
            s = ""
            for j in range(0, i+1):
                s += split[j]+'___'
            script += "    $('#{}div').show();\n".format(s)
        script += "    $('#{}___{}___div').show();\n".format(div_id, key.replace('/', slash).replace(':', colon).replace('.', dot))
        script += "    e.preventDefault();\n"
        script += "  }\n"
        script += "});\n"
    return html, script



def dropdown(li, text, div_id, reservations={}):
    html = ''
    #html += '    <div class="row row_j4spawner">\n'
    html += '    <div class="dropdown_j4j">\n'
    html += '      <label for="{div_id}" class="bg-primary text-center label_j4j">{text}</label>\n'.format(div_id=div_id, text=text)
    html += '      <div class="btn-group btn_group_j4spawner">\n'
    html += '        <button type="button" class="btn btn-primary dropdown-toggle form-control button_j4j" data-toggle="dropdown" aria-expanded="false" id="{div_id}" name="{div_id}_name" value="{default}">\n'.format(div_id=div_id, default=li[0])
    if li[0] == 'Docker':
        html += '          {}\n'.format("HDF-Cloud")
    else:
        html += '          {}\n'.format(li[0])
    html += '          <span class="caret"></span>\n'
    html += '        </button>\n'
    html += '        <ul class="dropdown-menu" name="uid" id="{}___ul">\n'.format(div_id)
    if len(reservations) > 0:
        for key in li:
            if reservations.get(key, {}).get('State') == 'INACTIVE':
                html += '          <li><a href="#" id="{div_id}___element___{key}" style="text-decoration:line-through; color:red">{key}</a></li>\n'.format(div_id=div_id, key=key)
            else:
                html += '          <li><a href="#" id="{div_id}___element___{key}">{key}</a></li>\n'.format(div_id=div_id, key=key)
    else:
        for key in li:
            if key == 'Docker':
                html += '          <li><a href="#" id="{div_id}___element___{key}">{key2}</a></li>\n'.format(div_id=div_id, key=key, key2="HDF-Cloud")
            else:
                html += '          <li><a href="#" id="{div_id}___element___{key}">{key}</a></li>\n'.format(div_id=div_id, key=key)
    html += '        </ul>\n'
    html += '      </div>\n'
    html += '    </div>\n'
    script  = ''
    for key in li:
        c = div_id.count('___')
        var = ''
        script += "jQuery('#"+div_id+"___element___"+key+"').click(function(e){\n"
        if c == 0:
            var = 'system'
        elif c == 1:
            var = 'account'
        elif c == 2:
            var = 'project'
        elif c == 3:
            var = 'partition'
        elif c == 4:
            var = 'reservation'
        script += "  if ( $('#"+var+"_input').val() === \""+key+"\" ){\n"
        script += "    e.preventDefault();\n"
        script += "  } else {\n"
        script += "    $('#{}').val('{}');\n".format(div_id, key)
        if key == "Docker":
            script += "    $('#{}').html('{} <span class=\"caret\"></span>');\n".format(div_id, "HDF-Cloud")
        else:
            script += "    $('#{}').html('{} <span class=\"caret\"></span>');\n".format(div_id, key)
        script += "    $('#{}_input').val('{}');\n".format(var, key)
        # If c == 0 -> show key system
        # if c == 1 -> show key account and system in div_id (split('___')[0/1])
        script += "    hideAll();\n"
        # show parent divs and my own div
        split = div_id.split('___')
        for i in range(1,len(split)):
            s = ""
            for j in range(0, i+1):
                s += split[j]+'___'
            script += "    $('#{}div').show();\n".format(s)
        script += "    $('#{}___{}___div').show();\n".format(div_id, key)
        # show child divs
        if c == 3:
            script += "    var reservation = $('#{}___{}').val();\n".format(div_id, key)
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}___{}___'+reservation+'___div').show();\n".format(div_id, key)
        if c == 2:
            script += "    var partition = $('#{}___{}').val();\n".format(div_id, key)
            script += "    var reservation = $('#{}___{}___'+partition).val();\n".format(div_id, key)
            script += "    $('#partition_input').val(''+partition);\n"
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}___{}___'+partition+'___div').show();\n".format(div_id, key)
            script += "    $('#{}___{}___'+partition+'___'+reservation+'___div').show();\n".format(div_id, key)
        if c == 1:
            script += "    var project = $('#{}___{}').val();\n".format(div_id, key)
            script += "    var partition = $('#{}___{}___'+project+'').val();\n".format(div_id, key)
            script += "    var reservation = $('#{}___{}___'+project+'___'+partition).val();\n".format(div_id, key)
            script += "    $('#project_input').val(''+project);\n"
            script += "    $('#partition_input').val(''+partition);\n"
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}___{}___'+project+'___div').show();\n".format(div_id, key)
            script += "    $('#{}___{}___'+project+'___'+partition+'___div').show();\n".format(div_id, key)
            script += "    $('#{}___{}___'+project+'___'+partition+'___'+reservation+'___div').show();\n".format(div_id, key)
        if c == 0:
            if key.lower() == "docker":
                script += "    var account2 = $('#{}___{}').val();\n".format(div_id, key)
                script += "    var account = account2.replace(\"/\", \"{}\").replace(\":\", \"{}\").replace(\".\", \"{}\");\n".format(slash, colon, dot)
            else:
                script += "    var account = $('#{}___{}').val();\n".format(div_id, key)
            script += "    var project = $('#{}___{}___'+account+'').val();\n".format(div_id, key)
            script += "    var partition = $('#{}___{}___'+account+'___'+project+'').val();\n".format(div_id, key)
            script += "    var reservation = $('#{}___{}___'+account+'___'+project+'___'+partition).val();\n".format(div_id, key)
            if key.lower() == "docker":
                script += "    $('#account_input').val(''+account2);\n"
            else:
                script += "    $('#account_input').val(''+account);\n"
            script += "    $('#project_input').val(''+project);\n"
            script += "    $('#partition_input').val(''+partition);\n"
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}___{}___'+account+'___div').show();\n".format(div_id, key)
            script += "    $('#{}___{}___'+account+'___'+project+'___div').show();\n".format(div_id, key)
            script += "    $('#{}___{}___'+account+'___'+project+'___'+partition+'___div').show();\n".format(div_id, key)
            script += "    $('#{}___{}___'+account+'___'+project+'___'+partition+'___'+reservation+'___div').show();\n".format(div_id, key)
        script += "    e.preventDefault();\n"
        script += "  }\n"
        script += "});\n"
    return html, script
