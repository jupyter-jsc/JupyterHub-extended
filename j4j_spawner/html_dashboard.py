'''
Created on May 17, 2019

@author: Tim Kreuzer
'''

def inputs(first, show=False):
    ret = ''
    ret += '<input autocomplete="off" id="first_input" name="first_input" value="'+first+'" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="dashboard_input" name="dashboard_input" value="undefined" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="second_input" name="second_input" value="undefined" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="third_input" name="third_input" value="undefined" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="fourth_input" name="fourth_input" value="undefined" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="fifth_input" name="fifth_input" value="undefined" style="display:'+('display' if show else 'none')+'">\n'
    ret += '<input autocomplete="off" id="sixth_input" name="sixth_input" value="undefined" style="display:'+('display' if show else 'none')+'">\n'
    return ret


def html_resource(dic, div_id):
    text = dic.get('TEXT')
    mima = dic.get('MINMAX')
    mima = [str(int(float(x)/dic.get('DIVISOR', 1))) for x in mima]
    text = text.replace('_min_', str(mima[0]))
    text = text.replace('_max_', str(mima[1]))
    ret  = ''
    ret += '  <div id="{div_id}_div" style="display: none">\n'.format(div_id=div_id)
    ret += '    <label for="{div_id}_input" id="{div_id}_label" class="resource_label_j4j">{text}</label>\n'.format(div_id=div_id, text=text)
    default_value = dic.get('DEFAULT')
    if default_value == '_max_':
        default_value = mima[1]
    elif default_value == '_min_':
        default_value = mima[0]
    ret += '    <input min="{}" max="{}" value="{}" class="input_j4j" name="{}_name" id="{}_input" type="number">\n'.format(mima[0], mima[1], default_value, div_id, div_id)
    ret += '  </div>\n'
    return ret


def filter_dashboard(user_dic, dashboards_dic):
    dashboard_filtered = {}
    for dboard in dashboards_dic.keys():
        for system in dashboards_dic.get(dboard, {}).get('system', []):
            if system in ['HDF-Cloud']:
                if dboard not in dashboard_filtered.keys():
                    dashboard_filtered[dboard] = {}
                dashboard_filtered[dboard]['HDF-Cloud'] = {}
                continue
            for account, v1 in user_dic.get(system, {}).items():
                if 'accounts' in dashboards_dic.get(dboard, {}).get(system, {}).keys() and account not in dashboards_dic.get(dboard, {}).get(system, {}).get('accounts', []):
                    continue
                for project, v2 in v1.items():
                    if 'projects' in dashboards_dic.get(dboard, {}).get(system, {}).keys() and project not in dashboards_dic.get(dboard, {}).get(system, {}).get('projects', []):
                        continue
                    for partition in v2.keys():
                        if 'partitions' in dashboards_dic.get(dboard, {}).get(system, {}).keys() and partition not in dashboards_dic.get(dboard, {}).get(system, {}).get('partitions', []):
                            continue
                        if dboard not in dashboard_filtered.keys():
                            dashboard_filtered[dboard] = {}
                            dashboard_filtered[dboard][system] = {}
                            dashboard_filtered[dboard][system][account] = {}
                            dashboard_filtered[dboard][system][account][project] = []
                        elif system not in dashboard_filtered[dboard].keys():
                            dashboard_filtered[dboard][system] = {}
                            dashboard_filtered[dboard][system][account] = {}
                            dashboard_filtered[dboard][system][account][project] = []
                        elif account not in dashboard_filtered[dboard][system].keys():
                            dashboard_filtered[dboard][system][account] = {}
                            dashboard_filtered[dboard][system][account][project] = []
                        elif project not in dashboard_filtered[dboard][system][account].keys():
                            dashboard_filtered[dboard][system][account][project] = []
                        dashboard_filtered[dboard][system][account][project].append(partition)
    return dashboard_filtered

def create_html_dashboard(second_list_all, user_dic, dashboards_dic, reservations_dic, checkboxes, maintenance, unicorex, overall_infos={}):
    html = ""
    dashboard_filter = filter_dashboard(user_dic, dashboards_dic)
    if len(maintenance) > 0:
        html += '<h3 class="maintenance_j4j">The following systems are not available right now: {}</h3>\n'.format(', '.join(maintenance))
        for m in maintenance:
            if m in user_dic.keys():
                del user_dic[m]
            for dash, infos in dashboards_dic.items():
                if m in infos.get('system', []):
                    infos.get('system', []).remove(m)
    second = ""
    second_list = []
    for isecond in second_list_all:
        if isecond in user_dic.keys():
            if len(second_list) == 0:
                second = isecond
            second_list.append(isecond)
    dashboard_list = []
    for idash in second_list_all:
        for idash_system in dashboards_dic.get(idash, {}).get('system', []):
            if idash_system in user_dic.keys() or idash_system == 'HDF-Cloud':
                if idash in dashboard_filter.keys():
                    dashboard_list.append(idash)
                    break
    for idash, dinfos in dashboards_dic.items():
        torm = []
        for system in dinfos.get('system', []):
            if system not in user_dic.keys():
                torm.append(system)
        for itorm in torm:
            dinfos.get('system', []).remove(itorm)
    third_list = sorted(list(user_dic.get(second, {}).keys()), key=lambda s: s.casefold())
    fourth_list = []
    fifth_list = []
    sixth_list = []
    if len(third_list) > 0:
        fourth_list = sorted(list(user_dic.get(second, {}).get(third_list[0], {}).keys()), key=lambda s: s.casefold())
    if len(fourth_list) > 0:
        fifth_list = list(user_dic.get(second, {}).get(third_list[0], {}).get(fourth_list[0], {}).keys())
    if len(fifth_list) > 0:
        sixth_list = list(user_dic.get(second, {}).get(third_list[0], {}).get(fourth_list[0], {}).get(fifth_list[0], {}).keys())
        
    html += '<div class="j4j">\n'
    script = "<script>\n"
    html += inputs("Dashboard")

    html += new_dropdown("firstdd", "Service", ["Dashboard"], "onChangeDD1", "onClickDD1")
    html += new_dropdown("dashboarddd", "Dashboard", dashboard_list, "onChangeDDDash", "onClickDDDash")
    html += new_dropdown("seconddd", "System", second_list, "onChangeDD2", "onClickDD2")
    html += new_dropdown("thirddd", "Account", third_list, "onChangeDD3", "onClickDD3")
    html += new_dropdown("fourthdd", "Project", fourth_list, "onChangeDD4", "onClickDD4")
    html += new_dropdown("fifthdd", "Partition", fifth_list, "onChangeDD5", "onClickDD5")
    html += new_dropdown("sixthdd", "Reservation", sixth_list, "onChangeDD6", "onClickDD6")

    t1, t2 = checkbox("reservation_cb", { "htmltext": "Show reservation info" }, "reservation")
    html += t1
    script += t2
    script += reservation_checkbox_script(reservations_dic)
    for service, v0 in checkboxes.items():
        for system, v1 in v0.items():
            for account, v2 in v1.items():
                for project, v3 in v2.items():
                    for partition, v4 in v3.items():
                        for cb_name, cb_infos in v4.items():
                            t1, t2 = checkbox(service+"_"+system+"_"+account+"_"+project+"_"+partition+"_"+cb_name, cb_infos, cb_name)
                            html += t1
                            script += t2
    script += checkbox_scripts(checkboxes)

    reservations = {}
    for system, reservation_types in reservations_dic.items():
        for reservation_infos in reservation_types.values():
            for reservation_values in reservation_infos.values():
                for reservation_name, reservation_value in reservation_values.items():
                    if not system in reservations.keys():
                        reservations[system] = {}
                    if not reservation_name in reservations.get(system, {}).keys():
                        reservations[system][reservation_name] = reservation_value
    for system, reservation in reservations.items():
        html += reservationInfo("reservation_{}_{}".format(system, "None"), {}, False)
        for name, infos in reservation.items():
            html += reservationInfo("reservation_{}_{}".format(system, name), infos, False)
    
    nodes =  {"MINMAX": [1, 256], "TEXT": "Nodes [_min_, _max_]", "DIVISOR": 1, "DEFAULT": 1}
    runtime = {"MINMAX": ["60", "86400"], "TEXT": "Runtime (min) [_min_, _max_]", "DIVISOR": 60, "DEFAULT": 30}
    gpus = {"MINMAX": [1, 4], "TEXT": "GPUs [_min_, _max_]", "DIVISOR": 1, "DEFAULT": "_max_"}
    cpus_per_node= {"MINMAX": [1, 48], "TEXT": "CPUs per node [_min_, _max_]", "DIVISOR": 1, "DEFAULT": "24"}
    html += html_resource(nodes, 'resource_nodes')
    html += html_resource(runtime, 'resource_runtime')
    html += html_resource(gpus, 'resource_gpus')
    html += html_resource(cpus_per_node, 'resource_cpus_per_node')
    script += resource_scripts(["nodes", "runtime", "gpus", "cpus_per_node"])   
    for dash, dinfos in dashboards_dic.items():
        if dash not in dashboard_list:
            continue
        if 'readmore' in dinfos.keys():
            html += dashinfo_text(dash, dinfos.get('readmore', []))
    html += system_readmore(unicorex)
    html += overall_readmore(overall_infos)
    html += '</div>\n'

    script += onchange_dd6()
    script += onchange_dd5(user_dic, reservations_dic)
    script += onchange_dd4(user_dic, dashboard_filter)
    script += onchange_dd3(user_dic, dashboard_filter)
    script += onchange_dd2(user_dic, dashboard_filter)
    script += onchange_dddash(dashboard_list, dashboards_dic, dashboard_filter)
    script += onchange_dd1(["Dashboard"], dashboard_list)
    script += onclick_dd6()
    script += onclick_dd5()
    script += onclick_dd4()
    script += onclick_dd3()
    script += onclick_dd2()
    script += onclick_dddash()
    script += onclick_dd1()
    script += dashinfo_hide(dashboards_dic.keys(), dashboard_list)
    script += init_script("Dashboard")
    script += system_readmore_hide(unicorex)
    script += "</script>\n"

    html += script
    return html

def overall_readmore(overall_infos):
    ret = ""
    for name, infos in overall_infos.items():
        ret += "<div style='display: block' id='readmore_overall_{}_div'>\n".format(name)
        for readmore in infos.get('readmore', []):
            ret += "  <p>{}</p>\n".format(readmore)
        ret += "</div>\n"
    return ret
    

def system_readmore(unicorex):
    ret = ""
    for system, infos in unicorex.items():
        ret += "<div style='display: none' id='readmore_system_{}_div'>\n".format(system)
        for readmore in infos.get('readmore', []):
            ret += "  <p>{}</p>\n".format(readmore)
        ret += "</div>\n"
    return ret

def system_readmore_hide(unicorex):
    ret = ""
    ret += "function readmore_system_hide(){\n"
    for system in unicorex.keys():
        ret += "  if( $('#readmore_system_" + system + "_div').length ){\n"
        ret += "    $('#readmore_system_" + system + "_div').hide();\n"
        ret += "  }\n"
    ret += "}\n"
    return ret

def dashinfo_hide(dashboards, dlist):
    ret = ""
    ret += "function dash_text_hide(){\n"
    for dash in dashboards:
        if dash in dlist:
            ret += "  $('#dashinfo_{}_text').hide();\n".format(dash.replace(" ", "_"))
    ret += "}\n"
    return ret

def dashinfo_text(div_id, texts):
    ret = ""
    ret += "<div style='display:none' id='dashinfo_{}_text'>\n".format(div_id.replace(" ", "_"))
    for text in texts: 
        ret += '<p>{text}</p>\n'.format(div_id=div_id, text=text)
    ret += "</div>\n"
    return ret

def resource_scripts(l):
    ret = ""
    ret += "function resources_hide() {\n"
    for i in l:
        ret += "  $('#resource_{}_div').hide();\n".format(i)
    ret += "}\n"
    return ret

def checkbox_scripts(checkboxes):
    ret = ""
    ret += "function checkboxes_hide() {\n"
    for service, v0 in checkboxes.items():
        for system, v1 in v0.items():
            for account, v2 in v1.items():
                for project, v3 in v2.items():
                    for partition, v4 in v3.items():
                        for cb_name in v4.keys():
                            ret += "  $('#{}_{}_{}_{}_{}_{}').hide();\n".format(service, system, account, project, partition, cb_name)
    ret += "}\n"
    ret += "function checkboxes_jlab() {\n"
    ret += "  var first = $('#first_input').val();\n"
    ret += "  var second = $('#second_input').val();\n"
    ret += "  var third = $('#third_input').val();\n"
    ret += "  var fourth = $('#fourth_input').val();\n"
    ret += "  var fifth = $('#fifth_input').val();\n"
    for service, v0 in checkboxes.items():
        for system, v1 in v0.items():
            for account, v2 in v1.items():
                for project, v3 in v2.items():
                    for partition, v4 in v3.items():
                        for cb_name in v4.keys():
                            ret += "  if ( (first == \""+service+"\" || \"ALL\" == \""+service+"\") ){\n"
                            ret += "    if ( (second == \""+system+"\" || \"ALL\" == \""+system+"\") ){\n"
                            ret += "      if ( (third == \""+account+"\" || \"ALL\" == \""+account+"\") ){\n"
                            ret += "        if ( (fourth == \""+project+"\" || \"ALL\" == \""+project+"\") ){\n"
                            ret += "          if ( (fifth == \""+partition+"\" || \"ALL\" == \""+partition+"\") ){\n"
                            ret += "            $('#{}_{}_{}_{}_{}_{}').show();\n".format(service, system, account, project, partition, cb_name)
                            ret += "          }\n"
                            ret += "        }\n"
                            ret += "      }\n"
                            ret += "    }\n"
                            ret += "  }\n"
    ret += "}\n"
    return ret
    

def reservation_checkbox_script(reservation_dic):
    ret = ""
    ret += "function reservation_hide_all() {\n"
    for system, sub in reservation_dic.items():
        for subsub in sub.get('Account', {}).values():
            for name in subsub.keys():
                ret += "  $('#reservation_{}_{}_div').hide();\n".format(system, name)
    for system, sub in reservation_dic.items():
        for subsub in sub.get('Project', {}).values():
            for name in subsub.keys():
                ret += "  $('#reservation_{}_{}_div').hide();\n".format(system, name)
    ret += "  document.getElementById('reservation_cb_input').checked = false;\n"
    ret += "  $('#reservation_cb').hide();\n"
    ret += "}\n"
    ret += "function reservation() {\n"
    ret += "  var res = $('#sixth_input').val();\n"
    ret += "  var system = $('#second_input').val();\n"
    ret += "  if ( document.getElementById('reservation_cb_input').checked ) {\n"
    ret += "    $('#reservation_'+system+'_'+res+'_div').show();\n"
    ret += "  } else { \n"
    ret += "    $('#reservation_'+system+'_'+res+'_div').hide();\n"
    ret += "  }\n"
    ret += "}\n"
    return ret

def onclick_dd1():
    ret = ""
    ret += "function onClickDD1(value) {\n"
    ret += '  var old = $("#first_input").val();\n'
    ret += '  if ( old == value ) {\n'
    ret += '    return;\n'
    ret += '  }\n'
    ret += '  dash_text_hide();\n'
    ret += '  readmore_system_hide();\n'
    ret += '  reservation_hide_all();\n'
    ret += '  checkboxes_hide();\n'
    ret += '  resources_hide();\n'
    ret += '  $("#sixthdd_div").hide();\n'
    ret += '  $("#fifthdd_div").hide();\n'
    ret += '  $("#fourthdd_div").hide();\n'
    ret += '  $("#thirddd_div").hide();\n'
    ret += '  $("#seconddd_div").hide();\n'
    ret += '  $("#dashboarddd_div").hide();\n'
    ret += '  $("#sixth_input").val("undefined");\n'
    ret += '  $("#fifth_input").val("undefined");\n'
    ret += '  $("#fourth_input").val("undefined");\n'
    ret += '  $("#third_input").val("undefined");\n'
    ret += '  $("#second_input").val("undefined");\n'
    ret += '  $("#dashboard_input").val("undefined");\n'
    ret += '  $("#firstdd").val(value).trigger("change");\n'
    ret += '  localStorage.setItem("first", value);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_dashboard", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_second", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_third", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fourth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fifth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_sixth", null);\n'
    ret += '  checkboxes_jlab();\n'
    ret += "}\n"
    return ret

def onclick_dddash():
    ret = ""
    ret += "function onClickDDDash(value) {\n"
    ret += '  var old = $("#dashboard_input").val();\n'
    ret += '  if ( old == value ) {\n'
    ret += '    return;\n'
    ret += '  }\n'
    ret += '  dash_text_hide();\n'
    ret += '  readmore_system_hide();\n'
    ret += '  reservation_hide_all();\n'
    ret += '  checkboxes_hide();\n'
    ret += '  resources_hide();\n'
    ret += '  $("#sixthdd_div").hide();\n'
    ret += '  $("#fifthdd_div").hide();\n'
    ret += '  $("#fourthdd_div").hide();\n'
    ret += '  $("#thirddd_div").hide();\n'
    ret += '  $("#seconddd_div").hide();\n'
    ret += '  $("#sixth_input").val("undefined");\n'
    ret += '  $("#fifth_input").val("undefined");\n'
    ret += '  $("#fourth_input").val("undefined");\n'
    ret += '  $("#third_input").val("undefined");\n'
    ret += '  $("#second_input").val("undefined");\n'
    ret += '  $("#dashboarddd").val(value).trigger("change");\n'
    ret += '  localStorage.setItem("first", $("#first_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_dashboard", value);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_second", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_third", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fourth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fifth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_sixth", null);\n'
    ret += '  checkboxes_jlab();\n'
    ret += "}\n"
    return ret

def onclick_dd2():
    ret = ""
    ret += "function onClickDD2(value) {\n"
    ret += '  var old = $("#second_input").val();\n'
    ret += '  if ( old == value ) {\n'
    ret += '    return;\n'
    ret += '  }\n'
    ret += '  reservation_hide_all();\n'
    ret += '  readmore_system_hide();\n'
    ret += '  checkboxes_hide();\n'
    ret += '  resources_hide();\n'
    ret += '  $("#sixthdd_div").hide();\n'
    ret += '  $("#fifthdd_div").hide();\n'
    ret += '  $("#fourthdd_div").hide();\n'
    ret += '  $("#thirddd_div").hide();\n'
    ret += '  $("#sixth_input").val("undefined");\n'
    ret += '  $("#fifth_input").val("undefined");\n'
    ret += '  $("#fourth_input").val("undefined");\n'
    ret += '  $("#third_input").val("undefined");\n'
    ret += '  $("#seconddd").val(value).trigger("change");\n'
    ret += '  localStorage.setItem("first", $("#first_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_dashboard", $("#dashboard_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_second", value);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_third", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fourth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fifth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_sixth", null);\n'
    ret += '  checkboxes_jlab();\n'
    ret += "}\n"
    return ret

def onclick_dd3():
    ret = ""
    ret += "function onClickDD3(value) {\n"
    ret += '  var old = $("#third_input").val();\n'
    ret += '  if ( old == value ) {\n'
    ret += '    return;\n'
    ret += '  }\n'
    ret += '  reservation_hide_all();\n'
    ret += '  checkboxes_hide();\n'
    ret += '  resources_hide();\n'
    ret += '  $("#sixthdd_div").hide();\n'
    ret += '  $("#fifthdd_div").hide();\n'
    ret += '  $("#fourthdd_div").hide();\n'
    ret += '  $("#sixth_input").val("undefined");\n'
    ret += '  $("#fifth_input").val("undefined");\n'
    ret += '  $("#fourth_input").val("undefined");\n'
    ret += '  $("#thirddd").val(value).trigger("change");\n'
    ret += '  localStorage.setItem("first", $("#first_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_dashboard", $("#dashboard_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_second", $("#second_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_third", value);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fourth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fifth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_sixth", null);\n'
    ret += '  checkboxes_jlab();\n'
    ret += "}\n"
    return ret

def onclick_dd4():
    ret = ""
    ret += "function onClickDD4(value) {\n"
    ret += '  var old = $("#fourth_input").val();\n'
    ret += '  if ( old == value ) {\n'
    ret += '    return;\n'
    ret += '  }\n'
    ret += '  reservation_hide_all();\n'
    ret += '  checkboxes_hide();\n'
    ret += '  resources_hide();\n'
    ret += '  $("#sixthdd_div").hide();\n'
    ret += '  $("#fifthdd_div").hide();\n'
    ret += '  $("#sixth_input").val("undefined");\n'
    ret += '  $("#fifth_input").val("undefined");\n'
    ret += '  $("#fourthdd").val(value).trigger("change");\n'
    ret += '  localStorage.setItem("first", $("#first_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_dashboard", $("#dashboard_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_second", $("#second_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_third", $("#third_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fourth", value);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fifth", null);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_sixth", null);\n'
    ret += '  checkboxes_jlab();\n'
    ret += "}\n"
    return ret

def onclick_dd5():
    ret = ""
    ret += "function onClickDD5(value) {\n"
    ret += '  var old = $("#fifth_input").val();\n'
    ret += '  if ( old == value ) {\n'
    ret += '    return;\n'
    ret += '  }\n'
    ret += '  reservation_hide_all();\n'
    ret += '  checkboxes_hide();\n'
    ret += '  resources_hide();\n'
    ret += '  $("#sixthdd_div").hide();\n'
    ret += '  $("#sixth_input").val("undefined");\n'
    ret += '  $("#fifthdd").val(value).trigger("change");\n'
    ret += '  localStorage.setItem("first", $("#first_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_dashboard", $("#dashboard_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_second", $("#second_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_third", $("#third_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fourth", $("#fourth_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fifth", value);\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_sixth", null);\n'
    ret += '  checkboxes_jlab();\n'
    ret += "}\n"
    return ret

def onclick_dd6():
    ret = ""
    ret += "function onClickDD6(value) {\n"
    ret += '  var old = $("#sixth_input").val();\n'
    ret += '  if ( old == value ) {\n'
    ret += '    return;\n'
    ret += '  }\n'
    ret += '  reservation_hide_all();\n'
    ret += '  $("#sixthdd").val(value).trigger("change");\n'
    ret += '  localStorage.setItem("first", $("#first_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_dashboard", $("#dashboard_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_second", $("#second_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_third", $("#third_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fourth", $("#fourth_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_fifth", $("#fifth_input").val());\n'
    ret += '  localStorage.setItem($("#first_input").val()+"_sixth", value);\n'
    ret += "}\n"
    return ret

def onchange_dd6():
    ret = ""
    ret += "function onChangeDD6() {\n"
    ret += "  var first = $('#firstdd').val();\n"
    ret += "  var second = $('#seconddd').val();\n"
    ret += "  var third = $('#thirddd').val();\n"
    ret += "  var fourth = $('#fourthdd').val();\n"
    ret += "  var fifth = $('#fifthdd').val();\n"
    ret += "  var value = $('#sixthdd').val();\n"
    ret += "  $('#sixth_input').val(value);\n"
    ret += "  $('#sixthdd').html(value + ' <span class=\\\"caret\\\"></span>');\n"
    ret += "  if ( value != \"None\" ) {\n"
    ret += "    $('#reservation_cb').show();\n"
    ret += "  }\n"
    ret += "}\n"
    return ret

def onchange_dd5(user_dic, reservations_dic={}):
    ret = ""
    ret += "function onChangeDD5() {\n"
    ret += "  var first = $('#firstdd').val();\n"
    ret += "  var second = $('#seconddd').val();\n"
    ret += "  var third = $('#thirddd').val();\n"
    ret += "  var fourth = $('#fourthdd').val();\n"
    ret += "  var value = $('#fifthdd').val();\n"
    ret += "  $('#fifth_input').val(value);\n"
    ret += '  checkboxes_jlab();\n'
    ret += "  $('#fifthdd').html(value + ' <span class=\\\"caret\\\"></span>');\n"
    for second, rest2 in user_dic.items():
        ret += '    if ( second == "'+ second +'" ) {\n'
        for third, rest3 in rest2.items():
            ret += '      if ( third == "'+ third +'" ) {\n'
            for fourth, rest4 in rest3.items():
                ret += '        if ( fourth == "'+ fourth +'" ) {\n'
                for fifth in rest4.keys():
                    ret += '          if ( value == "' + fifth + '" ) {\n'
                    reservations = []
                    if not fifth in ["LoginNode", "LoginNodeVis"]:
                        for name in reservations_dic.get(second, {}).get('Account', {}).get(third, {}).keys():
                            partition = reservations_dic.get(second, {}).get('Account', {}).get(third, {}).get(name, {}).get('PartitionName', "")
                            if name not in reservations:
                                if partition == '(null)' or partition == fifth:
                                    reservations.append(name)
                        for name in reservations_dic.get(second, {}).get('Project', {}).get(fourth, {}).keys():
                            partition = reservations_dic.get(second, {}).get('Project', {}).get(fourth, {}).get(name, {}).get('PartitionName', "")
                            if name not in reservations:
                                if partition == '(null)' or partition == fifth:
                                    reservations.append(name)
                    for resource_name, res_info in user_dic.get(second, {}).get(third, {}).get(fourth, {}).get(fifth, {}).items():
                        minmax = res_info.get('MINMAX')
                        mini = int(minmax[0])
                        maxi = int(minmax[1])
                        mini = int(mini / res_info.get('DIVISOR'))
                        maxi = int(maxi / res_info.get('DIVISOR'))
                        default = res_info.get('DEFAULT')
                        if default == "_max_":
                            default = maxi
                        elif default == "_min_":
                            default = mini
                        text = res_info.get('TEXT').replace('_min_', "{}".format(mini)).replace('_max_', "{}".format(maxi))
                        ret += "            $('#resource_{}_div').show();\n".format(resource_name.lower())
                        ret += "            $('#resource_"+ resource_name.lower() +"_input').attr({\"max\": "+ "{}".format(maxi) +", \"min\": "+ "{}".format(mini) +", \"value\": "+ "{}".format(default) +" });\n"
                        ret += "            $('#resource_"+ resource_name.lower() +"_label').text(\""+text+"\");\n"
                    if len(reservations) > 0:
                        reservations.insert(0, "None")
                        ret += '            $("#sixthdd_ul").html("");\n'
                        for name in reservations:
                            if reservations_dic.get(second, {}).get('Account', {}).get(third, {}).get(name, {}).get('State', "") == "INACTIVE" or reservations_dic.get(second, {}).get('Project', {}).get(fourth, {}).get(name, {}).get('State', "") == "INACTIVE":
                                ret += '            $("#sixthdd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" style="text-decoration:line-through; color:red" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDD6", div_prefix="sixthdd", key=name)
                            else:
                                ret += '            $("#sixthdd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDD6", div_prefix="sixthdd", key=name)
                        ret += '            $("#sixthdd").val("{}").trigger("change");\n'.format(reservations[0])
                        ret += "            $('#sixthdd_div').show();\n"
                    ret += '          }\n'
                ret += "        }\n"
            ret += "      }\n"
        ret += "    }\n"
    ret += "}\n"
    return ret

def onchange_dd4(user_dic, dashboard_filter):
    ret = ""
    ret += "function onChangeDD4() {\n"
    ret += "  var first = $('#firstdd').val();\n"
    ret += "  var dash = $('#dashboarddd').val();\n"
    ret += "  var second = $('#seconddd').val();\n"
    ret += "  var third = $('#thirddd').val();\n"
    ret += "  var value = $('#fourthdd').val();\n"
    ret += "  $('#fourth_input').val(value);\n"
    ret += "  $('#fourthdd').html(value + ' <span class=\\\"caret\\\"></span>');\n"
    for second, rest2 in user_dic.items():
        ret += '    if ( second == "'+ second +'" ) {\n'
        for third, rest3 in rest2.items():
            ret += '      if ( third == "'+ third +'" ) {\n'
            for fourth, rest4 in rest3.items():
                if len(rest4.keys()) > 0:
                    ret += '        if ( value == "'+ fourth +'" ) {\n'
                    rest4_list = []
                    if "LoginNode" in rest4.keys():
                        rest4_list.append("LoginNode")
                    if "LoginNodeVis" in rest4.keys():
                        rest4_list.append("LoginNodeVis")
                    for i in sorted(rest4.keys(), key=lambda s: s.casefold()):
                        if not i in ["LoginNode", "LoginNodeVis"]:
                            rest4_list.append(i)
                    ret += '          $("#fifthdd_ul").html("");\n'
                    for dashboard, v1 in dashboard_filter.items():
                        for system, v2 in v1.items():
                            for account, v3 in v2.items():
                                for project, v4 in v3.items():
                                    if len(v4) > 0:
                                        ret += '          if ( dash == "'+dashboard+'" && second == "'+system+'" && third == "'+account+'" && value == "'+project+'"){\n'
                                        for partition in v4:
                                            ret += '            $("#fifthdd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDD5", div_prefix="fifthdd", key=partition)
                                        ret += '            $("#fifthdd").val("{}").trigger("change");\n'.format(v4[0])
                                        ret += '          }\n'
                    ret += "          $('#fifthdd_div').show();\n"
                    ret += '          return;\n'
                    ret += '        }\n'
            ret += "      }\n"
        ret += "    }\n"
    ret += "}\n"
    return ret

def onchange_dd3(user_dic, dashboard_filter):
    ret = ""
    ret += "function onChangeDD3() {\n"
    ret += "  var first = $('#firstdd').val();\n"
    ret += "  var dash = $('#dashboarddd').val();\n"
    ret += "  var second = $('#seconddd').val();\n"
    ret += "  var value = $('#thirddd').val();\n"
    ret += "  $('#third_input').val(value);\n"
    ret += "  $('#thirddd').html(value + ' <span class=\\\"caret\\\"></span>');\n"
    for second, rest2 in user_dic.items():
        ret += '    if ( second == "'+ second +'" ) {\n'
        if second == "HDF-Cloud":
            ret += '      checkboxes_jlab();\n'
        for third, rest3 in rest2.items():
            if len(rest3.keys()) > 0:
                ret += '      if ( value == "'+ third +'" ) {\n'
                ret += '        $("#fourthdd_ul").html("");\n'
                for dashboard, v1 in dashboard_filter.items():
                    for system, v2 in v1.items():
                        for account, v3 in v2.items():
                            if len(v3.keys()) > 0:
                                ret += '        if ( dash == "'+dashboard+'" && second == "'+system+'" && value == "'+account+'"){\n'
                                for project in sorted(v3.keys(), key=lambda s: s.casefold()):
                                    ret += '          $("#fourthdd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDD4", div_prefix="fourthdd", key=project)
                                ret += '          $("#fourthdd").val("{}").trigger("change");\n'.format(sorted(v3.keys(), key=lambda s: s.casefold())[0])
                                ret += '        }\n'
                ret += "        $('#fourthdd_div').show();\n"
                ret += "      }\n"
        ret += "    }\n"
    ret += "}\n"
    return ret

def onchange_dd2(user_dic, dashboard_filter):
    ret = ""
    ret += "function onChangeDD2() {\n"
    ret += "  var first = $('#firstdd').val();\n"
    ret += "  var dash = $('#dashboarddd').val();\n"
    ret += "  var value = $('#seconddd').val();\n"
    ret += "  $('#second_input').val(value);\n"
    ret += "  $('#seconddd').html(value + ' <span class=\\\"caret\\\"></span>');\n"
    for second in user_dic.keys():
        ret += '    if ( value == "'+ second +'" ) {\n'
        ret += "      if( $('#readmore_system_" + second + "_div').length ){\n"
        ret += "        $('#readmore_system_{}_div').show();\n".format(second)
        ret += "      }\n"
        ret += '      if ( first != "Dashboard" || value != "HDF-Cloud" ) {\n'
        if second == 'HDF-Cloud':
            ret += "        $('#thirddd_label').html('Image');\n" 
        else:
            ret += "        $('#thirddd_label').html('Account');\n" 
        ret += '        $("#thirddd_ul").html("");\n'
        for dashboard, v1 in dashboard_filter.items():
            for system, v2 in v1.items():
                if len(v2.keys()) > 0:
                    ret += '        if ( dash == "'+dashboard+'" && value == "'+system+'"){\n'
                    for account in sorted(v2.keys(), key=lambda s: s.casefold()):
                        ret += '          $("#thirddd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDD3", div_prefix="thirddd", key=account)
                    ret += '          $("#thirddd").val("{}").trigger("change");\n'.format(sorted(v2.keys(), key=lambda s: s.casefold())[0])
                    ret += '        }\n'
        ret += "        $('#thirddd_div').show();\n"
        ret += "      }\n"
        ret += "    }\n"
    ret += "}\n"
    return ret

def onchange_dddash(dashboard_list, dashboard_dic, dashboard_filter):
    ret = ""
    ret += "function onChangeDDDash() {\n"
    ret += "  var first = $('#firstdd').val();\n"
    ret += "  var value = $('#dashboarddd').val();\n"
    ret += "  $('#dashboard_input').val(value);\n"
    ret += "  $('#dashboarddd').html(value + ' <span class=\\\"caret\\\"></span>');\n"
    for dash_name in dashboard_list:
        ret += '  if ( value == "'+ dash_name +'" ) {\n'
        ret += '    var tmp = "dashinfo_"+value+"_text";\n'
        ret += '    tmp = tmp.replace(" ", "_");\n'
        ret += "    if( $('#'+tmp+'').length ){\n"
        ret += "      $('#'+tmp+'').show();\n"
        ret += "    }\n"
        ret += '    $("#seconddd_ul").html("");\n'
        for second in dashboard_filter.get(dash_name, {}).keys():
            ret += '    $("#seconddd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDD2", div_prefix="seconddd", key=second)
        ret += '    $("#seconddd").val("{}").trigger("change");\n'.format(list(dashboard_filter.get(dash_name, {}).keys())[0])
        ret += "    $('#seconddd_div').show();\n"
        ret += "    if( $('#dashinfo_" + dash_name + "_text').length ){\n"
        ret += "      $('#dashinfo_" + dash_name + "_text').show();\n"
        ret += "    }\n"
        ret += "  }\n"
    ret += "}\n"
    return ret

def onchange_dd1(first_list, second_list):
    ret = ""
    ret += "function onChangeDD1() {\n"
    ret += "  var value = $('#firstdd').val();\n"
    ret += "  $('#first_input').val(value);\n"
    ret += "  $('#firstdd').html(value + ' <span class=\\\"caret\\\"></span>');\n"
    for first in first_list:
        ret += '  if ( value == "'+ first +'" ) {\n'
        ret += "    $('#seconddd_label').html(\"System\");\n"
        ret += "    $('#thirddd_label').html(\"Account\");\n"
        ret += "    $('#fourthdd_label').html(\"Project\");\n"
        ret += "    $('#fifthdd_label').html(\"Partition\");\n"
        ret += "    $('#sixthdd_label').html(\"Reservation\");\n"
        if first == "Dashboard":
            ret += "    $('#seconddd_div').hide();\n"
            ret += '    $("#dashboarddd_ul").html("");\n'
            for name in second_list:
                ret += '    $("#dashboarddd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDDDash", div_prefix="dashboarddd", key=name)
            ret += '    $("#dashboarddd").val("{}").trigger("change");\n'.format(second_list[0])
            ret += "    $('#dashboarddd_div').show();\n"
        else:
            ret += "    $('#dashboarddd_div').hide();\n"
            ret += '    $("#seconddd_ul").html("");\n'
            for name in second_list:
                ret += '    $("#seconddd_ul").append(\'<li><a href="#" onclick="{onclick}(\\\'{key}\\\')" id="{div_prefix}_{key}">{key}</a></li>\');\n'.format(onclick="onClickDD2", div_prefix="seconddd", key=name)
            ret += '    $("#seconddd").val("{}").trigger("change");\n'.format(second_list[0])
            ret += "    $('#seconddd_div').show();\n"
        ret += "  }\n"
    ret += "}\n"
    return ret

def init_script(first):
    ret = ""
    ret += "$(document).ready(function() {\n"
    ret += '  $("#optionsheader").html("'+first+' Options");\n'
    ret += '  $("#firstdd").val("'+first+'").trigger("change");\n'
    ret += '  var first = "{}";\n'.format(first)
    ret += '  var ls_second = localStorage.getItem(first+"_second");\n'
    ret += '  var ls_third = localStorage.getItem(first+"_third");\n'
    ret += '  var ls_fourth = localStorage.getItem(first+"_fourth");\n'
    ret += '  var ls_fifth = localStorage.getItem(first+"_fifth");\n'
    ret += '  var ls_sixth = localStorage.getItem(first+"_sixth");\n'
    if first == "Dashboard":
        ret += '  var ls_dash = localStorage.getItem(first+"_dashboard");\n'
        ret += '  if (! $("#dashboarddd_ul").html().includes(ls_dash)) {\n'
        ret += '    return;\n'
        ret += '  }\n'
        ret += '  if (ls_dash != null && ls_dash != "null") {\n'
        ret += '    onClickDDDash(ls_dash);\n'
    ret += '  if (ls_second != null && ls_second != "null") {\n'
    ret += '    if (! $("#seconddd_ul").html().includes(ls_second)) {\n'
    ret += '      return;\n'
    ret += '    }\n'
    ret += '    onClickDD2(ls_second);\n'
    ret += '    if (ls_third != null && ls_third != "null") {\n'
    ret += '      if (! $("#thirddd_ul").html().includes(ls_third)) {\n'
    ret += '        return;\n'
    ret += '      }\n'
    ret += '      onClickDD3(ls_third);\n'
    ret += '      if (ls_fourth != null && ls_fourth != "null") {\n'
    ret += '        if (! $("#fourthdd_ul").html().includes(ls_fourth)) {\n'
    ret += '          return;\n'
    ret += '        }\n'
    ret += '        onClickDD4(ls_fourth);\n'
    ret += '        if (ls_fifth != null && ls_fifth != "null") {\n'
    ret += '          if (! $("#fifthdd_ul").html().includes(ls_fifth)) {\n'
    ret += '            return;\n'
    ret += '          }\n'
    ret += '          onClickDD5(ls_fifth);\n'
    ret += '          if (ls_sixth != null && ls_sixth != "null") {\n'
    ret += '            if (! $("#sixthdd_ul").html().includes(ls_sixth)) {\n'
    ret += '              return;\n'
    ret += '            }\n'
    ret += '            onClickDD6(ls_sixth);\n'
    ret += '          }\n'
    ret += '        }\n'
    ret += '      }\n'
    ret += '    }\n'
    ret += '  }\n'
    if first == "Dashboard":
        ret += '  }\n'
    ret += '  checkboxes_jlab();\n'
    ret += "});\n"
    return ret

def reservationInfo(div_id, reservation, show):
    if show:
        html = '<div id="{}_div" class="reservation_info_j4j" style="display: display">\n'.format(div_id)
    else:
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
    return html

def new_dropdown(div_prefix, label_text, first_values, onChange, onClick, show=False):
    html = '  <div id="{div_prefix}_div" style="display:{show}">\n'.format(div_prefix=div_prefix, show = "display" if len(first_values) > 0 and show else "none" )
    html += '    <div class="dropdown_j4j">\n'
    html += '      <label for="{div_prefix}" id="{div_prefix}_label" class="bg-primary text-center label_j4j">{text}</label>\n'.format(div_prefix=div_prefix, text=label_text)
    html += '      <div class="btn-group btn_group_j4spawner">\n'
    html += '        <button type="button" onchange="{onchange}()" class="btn btn-primary dropdown-toggle form-control button_j4j" data-toggle="dropdown" aria-expanded="false" id="{div_prefix}" name="{div_prefix}_name" value="{default}">\n'.format(onchange=onChange, div_prefix=div_prefix, default= first_values[0] if len(first_values) > 0 else "")
    if len(first_values) > 0:
        html += '          {}\n'.format(first_values[0])
    html += '          <span class="caret"></span>\n'
    html += '        </button>\n'
    html += '        <ul class="dropdown-menu" name="uid" id="{}_ul">\n'.format(div_prefix)
    for key in first_values:
        html += '          <li><a href="#" onclick="{onclick}(\'{key}\')" id="{div_prefix}_{key}">{key}</a></li>\n'.format(onclick=onClick, div_prefix=div_prefix, key=key)
    html += '        </ul>\n'
    html += '      </div>\n'
    html += '    </div>\n'
    html += '  </div>\n'
    return html

def checkbox(div_id, cb_infos, onClick):
    text = cb_infos.get('htmltext', 'htmltext')
    tooltip = cb_infos.get('info', '')
    noqm = cb_infos.get('noqm', 'false').lower()=='true'
    html = ''
    script = ''
    html += '  <div id="{}" class="checkbox_div_j4j" style="display: none">\n'.format(div_id)
    if noqm:
        html += '    <li class="bg-primary list-group-item checkbox_li_j4j">{text}&nbsp;<img class="qm_j4j" id="{div_id}_image" src="https://jupyter-jsc.fz-juelich.de/hub/static/images/noqm.png" data-original-title="" title="" height="20">\n'.format(div_id=div_id, text=text)
    else:
        html += '    <li class="bg-primary list-group-item checkbox_li_j4j">{text}&nbsp;<img class="qm_j4j" id="{div_id}_image" src="https://jupyter-jsc.fz-juelich.de/hub/static/images/qm.png" data-original-title="" title="" height="20"><span id="{div_id}_tooltip" style="z-index: 5; padding: 5px; position: absolute; top: 43px; left:0px; background: #eeeeee; display: none">{tooltip}</span>\n'.format(div_id=div_id, text=text, tooltip=tooltip)
        if len(tooltip) > 0:
            script += 'document.getElementById("'+ div_id+'_image").addEventListener("mouseover", function() { document.getElementById("'+div_id+'_tooltip").style.display = "block"; });\n'
            script += 'document.getElementById("'+ div_id+'_image").addEventListener("mouseout", function() { document.getElementById("'+div_id+'_tooltip").style.display = "none"; });\n'
    html += '      <div class="material-switch pull-right" style="">\n'
    html += '        <input id="{div_id}_input" name="{div_id}_name" onClick="{onclick}()" class="form-control" type="checkbox">\n'.format(div_id=div_id, onclick=onClick)
    html += '        <label for="{div_id}_input" class="label-primary"></label>\n'.format(div_id=div_id)
    html += '      </div>\n'
    html += '    </li>\n'
    html += '  </div>\n'
    return html, script
