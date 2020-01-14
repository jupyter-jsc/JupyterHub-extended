'''
Created on May 17, 2019

@author: Tim Kreuzer
'''

import json

colon = '--colon--' # replace : with --colon-- in variable names
slash = '--slash--' # "
dot = '--dot--'     # "

def create_html(user_accs, reservations, partitions_path, stylepath, dockerimagespath, project_checkbox_path, maintenance):
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
    html += '  <div id="system_div" style="display:display">\n'
    t1, t2 = dropdown(user_accs_w_docker, 'System:', 'system')
    html += t1
    html += '  </div>\n'
    script += t2
    for system, accounts in user_accs.items():
        t1, t2 = html_system('system_'+system, accounts, resources_json.get(system, {}), reservations.get(system, {}), project_checkbox, disclaimer.get(system, False), system==sorted(user_accs.keys(), key=lambda s: s.casefold())[0])
        html += t1
        script += t2
    t1, t2 = docker('system_Docker', dockerimages, docker_show, project_checkbox)
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
        html += '  <div id="{div_id}_div" style="display:display">\n'.format(div_id=system)
    else:
        html += '  <div id="{div_id}_div" style="display:none">\n'.format(div_id=system)
    t1, t2 = docker_dropdown(dockerimages, "Docker Image:", system)
    html += t1
    script += t2
    for project_cb_name, project_cb in project_checkbox.get('DOCKER', {}).items():
        t1, t2 = checkbox(system+'_'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
        html += t1
        script += t2
    for project_cb_name, project_cb in project_checkbox.get('ALL', {}).items():
        if project_cb.get('docker', 'false').lower() == 'true':
            t1, t2 = checkbox(system+'_'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
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
        script += "  $('#system_{}_div').hide();\n".format(sys)
        if len(dic) == 0:
            continue
        for account, projects in dic.items():
            script += "  $('#system_{}_{}_div').hide();\n".format(sys, account)
            if len(projects) == 0:
                continue
            for project, partitions in projects.items():
                script += "  $('#system_{}_{}_{}_div').hide();\n".format(sys, account, project)
                if len(partitions) == 0:
                    continue
                for partition in partitions.keys():
                    script += "  $('#system_{}_{}_{}_{}_div').hide();\n".format(sys, account, project, partition)
                    script += "  $('#system_{}_{}_{}_{}_reservation_input').prop('checked', false);\n".format(sys, account, project, partition)
                    reservation_already_used = []
                    reservations_length = 0
                    for reservation_name, infos in reservations.get(sys, {}).get('Account', {}).get(account, {}).items():
                        if partition in infos.get('PartitionName'):
                            script += "  $('#system_{}_{}_{}_{}_reservation_{}_div').hide();\n".format(sys, account, project, partition, reservation_name)
                            reservation_already_used.append(reservation_name)
                            reservations_length += 1
                    for reservation_name, infos in reservations.get(sys, {}).get('Project', {}).get(project, {}).items():
                        if partition in infos.get('PartitionName'):
                            if reservation_name not in reservation_already_used:
                                script += "  $('#system_{}_{}_{}_{}_reservation_{}_div').hide();\n".format(sys, account, project, partition, reservation_name)
                                reservations_length += 1
                    if reservations_length > 0:
                        script += "  $('#system_{}_{}_{}_{}_reservation_None_div').hide();\n".format(sys, account, project, partition)
    # hide docker stuff, too
    script += "  $('#system_{}_div').hide();\n".format('Docker')
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
    system_name_list = system.split('_')
    system_name = ''
    if len(system_name_list) == 2:
        system_name = system_name_list[1].upper()
    accountlist = sorted(accounts.keys(), key=lambda s: s.casefold())
    if show:
        #html += '  <div id="{div_id}_div" class="machine_j4spawner" style="display:display">\n'.format(div_id=system)
        html += '  <div id="{div_id}_div" style="display:display">\n'.format(div_id=system)
    else:
        #html += '  <div id="{div_id}_div" class="machine_j4spawner" style="display:none">\n'.format(div_id=system)
        html += '  <div id="{div_id}_div" style="display:none">\n'.format(div_id=system)
    t1, t2 = dropdown(accountlist, 'Account:', system)
    html += t1
    script += t2
    for account, projects in accounts.items():
        projectlist = sorted(projects.keys(), key=lambda s: s.casefold())
        if account == accountlist[0]:
            #html += '  <div id="{div_id}_div" class="machine_j4spawner" style="display:display">\n'.format(div_id=system+'_'+account)
            html += '  <div id="{div_id}_div" style="display:display">\n'.format(div_id=system+'_'+account)
        else:
            #html += '  <div id="{div_id}_div" class="machine_j4spawner" style="display:none">\n'.format(div_id=system+'_'+account)
            html += '  <div id="{div_id}_div" style="display:none">\n'.format(div_id=system+'_'+account)
        t1, t2 = dropdown(projectlist, 'Project:', system+'_'+account)
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
                #html += '  <div id="{div_id}_div" class="machine_j4spawner" style="display:display">\n'.format(div_id=system+'_'+account+'_'+project)
                html += '  <div id="{div_id}_div" style="display:display">\n'.format(div_id=system+'_'+account+'_'+project)
            else:
                #html += '  <div id="{div_id}_div" class="machine_j4spawner" style="display:none">\n'.format(div_id=system+'_'+account+'_'+project)
                html += '  <div id="{div_id}_div" style="display:none">\n'.format(div_id=system+'_'+account+'_'+project)
            t1, t2 = dropdown(partitionlist, 'Partition:', system+'_'+account+'_'+project)
            html += t1
            script += t2
            for partition, resources in partitions_supported.items():
                if partition==partitionlist[0] and project==projectlist[0] and account==accountlist[0]:
                    html += '<div id="{}_div" style="display:display">\n'.format(system+'_'+account+'_'+project+'_'+partition)
                else:
                    html += '<div id="{}_div" style="display:none">\n'.format(system+'_'+account+'_'+project+'_'+partition)
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
                    t1, t2 = dropdown(reservationlist, 'Reservation:', system+'_'+account+'_'+project+'_'+partition, reservation_for_partition)
                    html += t1
                    script += t2
                    t1, t2 = checkbox(system+'_'+account+'_'+project+'_'+partition+'_reservation', "Show reservation info", "Show more information for your reservations")
                    html += t1
                    script += t2
                    for s in reservationlist:
                        t1,t2 = reservationInfo(system+'_'+account+'_'+project+'_'+partition+'_reservation_'+s, reservation_for_partition.get(s))
                        html += t1
                for resource, infos in resources.items():
                    html += html_resource(infos, system+'_'+account+'_'+project+'_'+partition+'_'+resource)
                html += '</div>\n'
            for project_cb_name, project_cb in project_checkbox.get(system_name, {}).items():
                if project in project_cb.get('projects', []):
                    t1, t2 = checkbox(system+'_'+account+'_'+project+'_'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
                    html += t1
                    script += t2
            html += '</div>\n'
        html += '</div>\n'
    for project_cb_name, project_cb in project_checkbox.get('ALL', {}).items():
        t1, t2 = checkbox(system+'_'+project_cb_name, project_cb.get('htmltext', 'htmltext'), project_cb.get('info', 'info'), project_cb.get('noqm', 'false').lower()=='true')
        html += t1
        script += t2
    #t1, t2 = checkbox(system+'_tutorial', "<b><i><span class=\"checkbox_span_j4j\">For Jupyter-beginner:</span></i></b>&nbsp;Download Jupyter@JSC-Tutorial", "When activated a git repository with examples for Jupyter Notebooks will be downloaded to ~/Jupyter@JSC-Tutorial")
    #html += t1
    #script += t2
    #t1, t2 = checkbox(system+'_loadmodules',"Load modules from ~/."+system.split('_')[1]+"_jupyter_modules.sh","With this option you can load additional modules.<br>Do not use \"module --force purge\" or similar commands!<br>Example for ~/."+system+"_jupyter_modules.sh:<br>\&emsp;module load mod1;<br>\&emsp;module load mod2;")
    #html += t1
    #script += t2
    html += '  <p><font size="+1">Overview of installed <a href="https://nbviewer.jupyter.org/github/kreuzert/Jupyter-JSC/blob/master/Extensions.ipynb" target="_blank">extensions</a>\n'
    #if disclaimer:
    #    html += '  <br><i><span class="checkbox_span_j4j">Please ensure that the project can use the partition</span></i>'
    html += '  </font></p>'
    html += '</div>\n'
    return html, script

def reservationInfo(div_id, reservation):
    html = '<div id="{}_div" class="reservation_info_j4j" style="display: none">\n'.format(div_id)
    html += '  <table class="table_j4j">\n'
    html += '    <tr class="table_tr_j4j">\n'
    tmp = div_id.split('_')
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
    if '_reservation' == div_id[-len('_reservation'):]:
        script += "$('#"+div_id+"_input').click(function() {\n"
        script += "  var reservation = $('#reservation_input').val();\n"
        script += "  $('#"+div_id+"_'+reservation+'_div').toggle(this.checked);\n"
        script += "});\n"
        """
        script += "jQuery('#"+div_id+"').change(function(e){\n"
        script += "  var reservation = $('#reservation_input').val();\n"
        script += "  if($('#"+div_id+"_input').is(\":checked\")) {\n"
        script += "    console.log('show infos');\n"
        script += "    jQuery('#"+div_id+"_'+reservation+'_div').show();\n"
        script += "  } else {\n"
        script += "    console.log('hide infos');\n"
        script += "    jQuery('#"+div_id+"_'+reservation+'_div').hide();\n"
        script += "  }\n"
        script += "});\n"
        """
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
    html += '        <ul class="dropdown-menu" name="uid" id="{}_ul">\n'.format(div_id)
    for key in li:
        html += '          <li><a href="#" id="{div_id}_element_{key}">{key_name}</a></li>\n'.format(div_id=div_id, key=key.replace('/', slash).replace(':', colon).replace('.', dot), key_name=key)
    html += '        </ul>\n'
    html += '      </div>\n'
    html += '    </div>\n'
    script  = ''
    for key in li:
        script += "jQuery('#"+div_id+"_element_"+key.replace('/', slash).replace(':', colon).replace('.', dot)+"').click(function(e){\n"
        var = 'account'
        script += "  if ( $('#"+var+"_input').val() === \""+key+"\" ){\n"
        script += "    e.preventDefault();\n"
        script += "  } else {\n"
        script += "    $('#{}').val('{}');\n".format(div_id, key)
        script += "    $('#{}').html('{} <span class=\"caret\"></span>');\n".format(div_id, key)
        script += "    $('#{}_input').val('{}');\n".format(var, key)
        script += "    hideAll();\n"
        split = div_id.split('_')
        for i in range(1,len(split)):
            s = ""
            for j in range(0, i+1):
                s += split[j]+'_'
            script += "    $('#{}div').show();\n".format(s)
        script += "    $('#{}_{}_div').show();\n".format(div_id, key.replace('/', slash).replace(':', colon).replace('.', dot))
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
    html += '        <ul class="dropdown-menu" name="uid" id="{}_ul">\n'.format(div_id)
    if len(reservations) > 0:
        for key in li:
            if reservations.get(key, {}).get('State') == 'INACTIVE':
                html += '          <li><a href="#" id="{div_id}_element_{key}" style="text-decoration:line-through; color:red">{key}</a></li>\n'.format(div_id=div_id, key=key)
            else:
                html += '          <li><a href="#" id="{div_id}_element_{key}">{key}</a></li>\n'.format(div_id=div_id, key=key)
    else:
        for key in li:
            if key == 'Docker':
                html += '          <li><a href="#" id="{div_id}_element_{key}">{key2}</a></li>\n'.format(div_id=div_id, key=key, key2="HDF-Cloud")
            else:
                html += '          <li><a href="#" id="{div_id}_element_{key}">{key}</a></li>\n'.format(div_id=div_id, key=key)
    html += '        </ul>\n'
    html += '      </div>\n'
    html += '    </div>\n'
    script  = ''
    for key in li:
        c = div_id.count('_')
        var = ''
        script += "jQuery('#"+div_id+"_element_"+key+"').click(function(e){\n"
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
        # if c == 1 -> show key account and system in div_id (split('_')[0/1])
        script += "    hideAll();\n"
        # show parent divs and my own div
        split = div_id.split('_')
        for i in range(1,len(split)):
            s = ""
            for j in range(0, i+1):
                s += split[j]+'_'
            script += "    $('#{}div').show();\n".format(s)
        script += "    $('#{}_{}_div').show();\n".format(div_id, key)
        # show child divs
        if c == 3:
            script += "    var reservation = $('#{}_{}').val();\n".format(div_id, key)
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}_{}_'+reservation+'_div').show();\n".format(div_id, key)
        if c == 2:
            script += "    var partition = $('#{}_{}').val();\n".format(div_id, key)
            script += "    var reservation = $('#{}_{}_'+partition).val();\n".format(div_id, key)
            script += "    $('#partition_input').val(''+partition);\n"
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}_{}_'+partition+'_div').show();\n".format(div_id, key)
            script += "    $('#{}_{}_'+partition+'_'+reservation+'_div').show();\n".format(div_id, key)
        if c == 1:
            script += "    var project = $('#{}_{}').val();\n".format(div_id, key)
            script += "    var partition = $('#{}_{}_'+project+'').val();\n".format(div_id, key)
            script += "    var reservation = $('#{}_{}_'+project+'_'+partition).val();\n".format(div_id, key)
            script += "    $('#project_input').val(''+project);\n"
            script += "    $('#partition_input').val(''+partition);\n"
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}_{}_'+project+'_div').show();\n".format(div_id, key)
            script += "    $('#{}_{}_'+project+'_'+partition+'_div').show();\n".format(div_id, key)
            script += "    $('#{}_{}_'+project+'_'+partition+'_'+reservation+'_div').show();\n".format(div_id, key)
        if c == 0:
            if key.lower() == "docker":
                script += "    var account2 = $('#{}_{}').val();\n".format(div_id, key)
                script += "    var account = account2.replace(\"/\", \"{}\").replace(\":\", \"{}\").replace(\".\", \"{}\");\n".format(slash, colon, dot)
            else:
                script += "    var account = $('#{}_{}').val();\n".format(div_id, key)
            script += "    var project = $('#{}_{}_'+account+'').val();\n".format(div_id, key)
            script += "    var partition = $('#{}_{}_'+account+'_'+project+'').val();\n".format(div_id, key)
            script += "    var reservation = $('#{}_{}_'+account+'_'+project+'_'+partition).val();\n".format(div_id, key)
            if key.lower() == "docker":
                script += "    $('#account_input').val(''+account2);\n"
            else:
                script += "    $('#account_input').val(''+account);\n"
            script += "    $('#project_input').val(''+project);\n"
            script += "    $('#partition_input').val(''+partition);\n"
            script += "    $('#reservation_input').val(''+reservation);\n"
            script += "    $('#{}_{}_'+account+'_div').show();\n".format(div_id, key)
            script += "    $('#{}_{}_'+account+'_'+project+'_div').show();\n".format(div_id, key)
            script += "    $('#{}_{}_'+account+'_'+project+'_'+partition+'_div').show();\n".format(div_id, key)
            script += "    $('#{}_{}_'+account+'_'+project+'_'+partition+'_'+reservation+'_div').show();\n".format(div_id, key)
        script += "    e.preventDefault();\n"
        script += "  }\n"
        script += "});\n"
    return html, script
