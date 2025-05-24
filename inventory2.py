#!/usr/bin/env python

#-------------------------------------------------------------------------------
# Name:        Linux Inventory Tool
#
# Author:      Nikolay Sisyukin
# URL:         https://nikolay.sisyukin.ru/
#
# Created:     31.08.2024
# Copyright:   (c) Nikolay Sisyukin 2024
# Licence:     MIT License
#-------------------------------------------------------------------------------

GB = 2 ** 30  #  1GB in bytes

import json, sys, os
import codecs
from operator import itemgetter

# ----------------------------------------------------------------------

def readJSONfromFile(filename):
    with codecs.open(filename, 'r', encoding='UTF-8') as f:
        return json.load(f)

# ----------------------------------------------------------------------

def dumpJSONtoFile(filename, data, mode='w', maxsize=-1):
    if data is None:
        return
    if maxsize == -1:
        filename = "{}.json".format(filename)
        with codecs.open(filename, mode, encoding="UTF-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return
    if maxsize > 0:
        file_counter = 1
        part_of_data = {}
        for key, value in data.items():
            if len(json.dumps(part_of_data, ensure_ascii=False, indent=4)) > maxsize:
                part_filename = "{}_{}.json".format(filename, file_counter)
                with codecs.open(part_filename, mode, encoding="UTF-8") as f:
                    json.dump(part_of_data, f, ensure_ascii=False, indent=4)
                file_counter += 1
                part_of_data = {key: value}
            else:
                part_of_data[key] = value
        if len(part_of_data) > 0:
            part_filename = "{}_{}.json".format(filename, file_counter)
            with codecs.open(part_filename, mode, encoding="UTF-8") as f:
                json.dump(part_of_data, f, ensure_ascii=False, indent=4)
        return

# ----------------------------------------------------------------------

def readLINEfromFile(filename):
    with codecs.open(filename, 'r', encoding='UTF-8') as f:
        return f.readline().split('\n')[0]
 
# ----------------------------------------------------------------------

def readLINESfromFile(filename):
    with codecs.open(filename, 'r', encoding='UTF-8') as f:
        return f.read().splitlines()

# ----------------------------------------------------------------------

def assing_if_is(value, key):
    if key in value.keys():
        if value[key] != 'None':
            return value[key]
        else:
            return None
    else:
        return None

# ----------------------------------------------------------------------

def parse_lshw_l0(lshw_data, inventory):
    if isinstance(lshw_data, list):
        for lshw_data_element in lshw_data:
            parse_lshw_l1(lshw_data_element, inventory)
            if 'children' in lshw_data_element.keys():
                parse_lshw_l0(lshw_data_element['children'], inventory)
    elif isinstance(lshw_data, dict):
        if 'children' in lshw_data.keys():
            parse_lshw_l1(lshw_data, inventory)
            parse_lshw_l0(lshw_data['children'], inventory)
        else:
            parse_lshw_l1(lshw_data, inventory)
            return

# ----------------------------------------------------------------------

def parse_lshw_l1(lshw_data, inventory):
    if 'description' in lshw_data.keys():

        if lshw_data['description'].lower() == 'computer':
            inventory['system_vendor'] = assing_if_is(lshw_data, 'vendor')
            inventory['system_platform'] = assing_if_is(lshw_data, 'product')
            inventory['system_platform_version'] = assing_if_is(lshw_data, 'version')
            inventory['system_serial'] = assing_if_is(lshw_data, 'serial')
            if inventory['system_platform'] is not None:
                if ('kvm' in inventory['system_platform'].lower() or
                    'vmware' in inventory['system_platform'].lower() or
                    'bochs' in inventory['system_vendor'].lower()):
                    inventory['is_vm'] = True

        if lshw_data['description'].lower() == 'motherboard':
            inventory['mb_vendor'] = assing_if_is(lshw_data, 'vendor')
            inventory['mb_model'] = assing_if_is(lshw_data, 'product')
            inventory['mb_version'] = assing_if_is(lshw_data, 'version')
            inventory['mb_serial'] = assing_if_is(lshw_data, 'serial')

        if lshw_data['description'].lower() == 'bios':
            inventory['mb_bios_vendor'] = assing_if_is(lshw_data, 'vendor')
            inventory['mb_bios_version'] = assing_if_is(lshw_data, 'version')
            inventory['mb_bios_date'] = assing_if_is(lshw_data, 'date')

        if lshw_data['description'].lower() == 'cpu' and 'product' in lshw_data.keys():
            inventory['cpu_model'] = lshw_data['product']
            inventory['cpu_count'] += 1
            if 'configuration' in lshw_data.keys():
                if 'cores' in lshw_data['configuration'].keys():
                    inventory['cpu_count_of_all_cores'] += int(lshw_data['configuration']['cores'])
                else:
                    inventory['cpu_count_of_all_cores'] += 1
            else:
                inventory['cpu_count_of_all_cores'] += 1


        if (lshw_data['description'].lower() == 'vga compatible controller' or
            (lshw_data['id'].lower() == 'display' and lshw_data['class'].lower() == 'display')):
            temp_vga = {}
            temp_vga['vga_vendor'] = assing_if_is(lshw_data, 'vendor')
            temp_vga['vga_model'] = assing_if_is(lshw_data, 'product')
            inventory['vga'].append(temp_vga)

        if lshw_data['class'].lower() == 'power' and 'power' in lshw_data['id'].lower():
            temp_psu = {}
            temp_psu['vendor'] = assing_if_is(lshw_data, 'vendor')
            temp_psu['model'] = assing_if_is(lshw_data, 'product')
            temp_psu['serial'] = assing_if_is(lshw_data, 'serial')
            temp_psu['units'] = assing_if_is(lshw_data, 'units')
            temp_psu['capacity'] = assing_if_is(lshw_data, 'capacity')
            inventory['psu'].append(temp_psu)
            inventory['psu_count'] += 1

        if lshw_data['class'].lower() == 'storage' and lshw_data['id'].lower() != 'nvme':
            temp_storage = {}
            temp_storage['vendor'] = assing_if_is(lshw_data, 'vendor')
            temp_storage['model'] = assing_if_is(lshw_data, 'product')
            temp_storage['description'] = assing_if_is(lshw_data, 'description')            
            temp_storage['serial'] = assing_if_is(lshw_data, 'serial')
            inventory['storages'].append(temp_storage)

        if lshw_data['class'].lower() == 'storage' and lshw_data['id'].lower() == 'nvme':
            temp_disk = {}

            temp_disk['model'] = assing_if_is(lshw_data, 'product')
            if 'children' in lshw_data.keys():
                for temp in lshw_data['children']:
                    if 'size' in temp.keys():
                        temp_disk['size_in_gb'] = assing_if_is(temp, 'size')
                        if isinstance(temp_disk['size_in_gb'], int):
                            temp_disk['size_in_gb'] //= GB
                        break

            temp_disk['serial'] = assing_if_is(lshw_data, 'serial')
            temp_disk['fw_version'] = assing_if_is(lshw_data, 'version')
            temp_disk['logicalname'] = assing_if_is(lshw_data, 'logicalname')
            
            inventory['disks'].append(temp_disk)

        if lshw_data['class'].lower() == 'disk' and 'nvme' not in lshw_data['description'].lower():
            temp_disk = {}
            temp_disk['model'] = assing_if_is(lshw_data, 'product')
            temp_disk['size_in_gb'] = assing_if_is(lshw_data, 'size')
            if isinstance(temp_disk['size_in_gb'], int):
                temp_disk['size_in_gb'] //= GB
            temp_disk['serial'] = assing_if_is(lshw_data, 'serial')
            temp_disk['fw_version'] = assing_if_is(lshw_data, 'version')
            temp_disk['logicalname'] = assing_if_is(lshw_data, 'logicalname')
            inventory['disks'].append(temp_disk)

        if lshw_data['description'].lower() == 'system memory':
            inventory['memory_size_in_gb'] = lshw_data['size'] / GB

        if (lshw_data['class'].lower() == 'memory' and
            'cache' not in lshw_data['description'] and
            'bios' not in lshw_data['description'].lower() and
            'system memory' not in lshw_data['description'].lower() and
            'size' in lshw_data.keys()):
            temp_ram_module = {}
            temp_ram_module['slot'] = lshw_data['slot']
            temp_ram_module['vendor'] = assing_if_is(lshw_data, 'vendor')
            temp_ram_module['model'] = assing_if_is(lshw_data, 'product')
            temp_ram_module['type'] = lshw_data['description']
            temp_ram_module['frequency_in_mhz'] = assing_if_is(lshw_data, 'clock')
            if isinstance(temp_ram_module['frequency_in_mhz'], int):
                temp_ram_module['frequency_in_mhz'] //= 1000000
            temp_ram_module['serial'] = assing_if_is(lshw_data, 'serial')
            temp_ram_module['size_in_gb'] = lshw_data['size'] / GB
            inventory['memory_modules_count'] += 1
            inventory['memory_modules'].append(temp_ram_module)

        if (lshw_data['class'].lower() == 'network' and
            'logicalname' in lshw_data.keys()):
            if lshw_data['logicalname'] in inventory['network_interfaces'].keys():
                if 'vendor' in lshw_data.keys():
                    inventory['network_interfaces'][lshw_data['logicalname']]['vendor'] = lshw_data['vendor']
                if 'product' in lshw_data.keys():
                    inventory['network_interfaces'][lshw_data['logicalname']]['product'] = lshw_data['product']

        elif (lshw_data['class'].lower() == 'network' and 'logicalname' not in lshw_data.keys()):
            temp_id = "{}{}".format(lshw_data['configuration']['driver'], inventory['network_nonstd_id'])
            inventory['network_interfaces'][temp_id] = {}
            if 'vendor' in lshw_data.keys():
                inventory['network_interfaces'][temp_id]['vendor'] = lshw_data['vendor']
            if 'product' in lshw_data.keys():
                inventory['network_interfaces'][temp_id]['product'] = lshw_data['product']
            inventory['network_nonstd_id'] += 1

# ----------------------------------------------------------------------

def parse_storcli_l0(storcli_data, inventory):
    for controller in storcli_data['Controllers']:
        for drive in controller['Response Data'].values():
            if isinstance(drive, dict):
                for drive_detail in drive.values():
                    if isinstance(drive_detail, dict):
                        if 'SN' in drive_detail.keys() and 'Model Number' in drive_detail.keys():
                            temp_disk = {}
                            temp_disk['model'] = assing_if_is(drive_detail, 'Model Number')
                            temp_disk['size_raw'] = assing_if_is(drive_detail, 'Raw size')
                            temp_disk['serial'] = assing_if_is(drive_detail, 'SN').split()[0]
                            temp_disk['wwn'] = assing_if_is(drive_detail, 'WWN')
                            temp_disk['fw_version'] = assing_if_is(drive_detail, 'Firmware Revision')
                            inventory['disks'].append(temp_disk)

# ----------------------------------------------------------------------

def inventory(to_screen=True, to_file=True, filename='result'):

    # ----------------------------------------------------------------------
    # PRERUN BEGIN

    inventory = {}

    inventory['is_vm'] = False

    inventory['date_of_inventory'] = None
    inventory['script_version'] = None

    inventory['os_hostname'] = None
    inventory['os_version'] = None
    inventory['os_core'] = None
    inventory['os_users'] = []
    inventory['os_users_sudo'] = []
    inventory['os_users_wheel'] = []
    inventory['os_users_ssh'] = []
    inventory['os_ssh_port'] = None

    inventory['os_ssl_version'] = None
    inventory['os_ssh_version'] = None

    inventory['packages_version'] = {}

    inventory['system_vendor'] = None
    inventory['system_platform'] = None
    inventory['system_platform_version'] = None
    inventory['system_serial'] = None

    inventory['cpu_model'] = None
    inventory['cpu_count'] = 0
    inventory['cpu_count_of_all_cores'] = 0

    inventory['mb_vendor'] = None
    inventory['mb_model'] = None
    inventory['mb_version'] = None
    inventory['mb_serial'] = None

    inventory['mb_bios_vendor'] = None
    inventory['mb_bios_version'] = None
    inventory['mb_bios_date'] = None

    inventory['memory_size_in_gb'] = 0
    inventory['memory_modules_count'] = 0
    inventory['memory_modules'] = []

    inventory['vga'] = []

    inventory['storages'] = []

    inventory['disks'] = []

    inventory['volumes'] = []

    inventory['psu_count'] = 0
    inventory['psu'] = []

    inventory['network_all_ip_addresses'] = []
    inventory['network_routes_all'] = {}
    inventory['network_interfaces'] = {}
    inventory['network_listen_ports_list'] = []
    inventory['network_listen_ports'] = {}
    inventory['network_nonstd_id'] = 0

    inventory['docker_containers'] = []

    # PRERUN END
    # ----------------------------------------------------------------------
    # OS BEGIN

    inventory['date_of_inventory'] = readLINEfromFile('date_of_inventory.txt')
    inventory['script_version'] = readLINEfromFile('VERSION')

    inventory['os_hostname'] = readLINEfromFile('os_hostname.txt')
    inventory['os_version'] = readLINEfromFile('os_version.txt')
    inventory['os_core'] = readLINEfromFile('os_core.txt')
    inventory['os_users'] =  sorted(readLINESfromFile('os_users.txt'))
    
    temp_users_line = readLINEfromFile('os_users_sudo.txt')
    if len(temp_users_line) > 0:
        inventory['os_users_sudo'] = sorted(temp_users_line.split(','))
    
    temp_users_line = readLINEfromFile('os_users_wheel.txt')
    if len(temp_users_line) > 0:    
        inventory['os_users_wheel'] = sorted(temp_users_line.split(','))

    inventory['os_users_ssh'] = sorted(readLINEfromFile('os_users_ssh.txt').split())
    inventory['os_ssh_port'] = int(readLINEfromFile('os_ssh_port.txt'))
    inventory['os_ssl_version'] = readLINEfromFile('os_ssl_version.txt')
    inventory['os_ssh_version'] = readLINEfromFile('os_ssh_version.txt')

    if os.path.exists('packages_apt.txt'):
        package_filename = 'packages_apt.txt'
        flag1 = 'apt'
        temp_packages_list = readLINESfromFile(package_filename)[1::]
        
    elif os.path.exists('packages_yum.txt'):
        package_filename = 'packages_yum.txt'
        flag1 = 'yum'
        temp_packages_list = readLINESfromFile(package_filename)[2::]

    temp_packages_dict = {}
    flag2_skip = False

    for line_i, line in enumerate(temp_packages_list):
        if flag2_skip:
            flag2_skip = False
            continue
        t_name = line.split('/')[0] if flag1 == 'apt' else line.split()[0]
        if len(line.split()) > 1 and not line.startswith(' '):
            t_ver = line.split()[1].split('-')[0]
        elif temp_packages_list[line_i + 1].startswith(' '):
            t_ver = temp_packages_list[line_i + 1].split()[0].split('-')[0]
            flag2_skip = True
        if ':' in t_ver:
            temp_packages_dict[t_name] = t_ver.split(':')[1]
        else:
            temp_packages_dict[t_name] = t_ver

    inventory['packages_version'] = temp_packages_dict

    # OS END
    # ----------------------------------------------------------------------
    # NETWORK BEGIN

    netstat = [record.split() for record in readLINESfromFile('netstat.txt')]

    for rec in netstat:
        rec.append(int(rec[3].split(':')[-1]))
        rec.append(rec[3].replace('{}'.format(rec[-1]), ''))

    netstat = sorted(netstat, key=itemgetter(-1))
    netstat = sorted(netstat, key=itemgetter(-2))

    for rec in netstat:
        id = 'port {}/{} on {}'.format(rec[0], rec[-2], rec[-1])[:-1:]
        inventory['network_listen_ports'][id] = {}
        inventory['network_listen_ports'][id]['listen_proto'] = rec[0]
        inventory['network_listen_ports'][id]['listen_port'] = str(rec[-2])
        inventory['network_listen_ports'][id]['listen_ip'] = rec[-1][:-1:]
        inventory['network_listen_ports'][id]['listen_pid_program'] = rec[-3]
        if str(rec[-2]) not in inventory['network_listen_ports_list']:
            inventory['network_listen_ports_list'].append(str(rec[-2]))

    if os.path.exists('docker.json'):
        docker_raw = readJSONfromFile('docker.json')
        docker = []
        docker_ports = {}
        
        for container in docker_raw:
            docker_temp = {}
            docker_temp['name'] = container['Names']
            docker_temp['id'] = container['ID']
            docker_temp['image'] = container['Image']
            docker_temp['ports'] = container['Ports'].split(', ') if len(container['Ports']) > 0 else []
            for port in docker_temp['ports']:
                if '0.0.0.0:' in port or ':::' in port:
                    if '0.0.0.0:' in port:
                        name_temp_port = port.split(':')[-1].split('->')[0]
                        name_temp_proto = port.split('/')[-1]
                        name_temp_ip = '0.0.0.0'#port.split(':')[0]
                    elif ':::' in port:
                        name_temp_port = port.split(':')[-1].split('->')[0]
                        name_temp_proto = port.split('/')[-1]+'6'
                        name_temp_ip = '::'#port.split(':')[0]
                    name_temp = 'port {}/{} on {}'.format(name_temp_proto, name_temp_port, name_temp_ip)
                    if name_temp in inventory['network_listen_ports'].keys():
                        docker_ports[name_temp] = {}
                        docker_ports[name_temp]['listen_proto'] = name_temp_proto
                        docker_ports[name_temp]['listen_port'] = name_temp_port
                        docker_ports[name_temp]['listen_ip'] = name_temp_ip
                        docker_ports[name_temp]['listen_container_name'] = docker_temp['name']
                        docker_ports[name_temp]['listen_container_image'] = docker_temp['image']
                        docker_ports[name_temp]['listen_container_id'] = docker_temp['id']
                        inventory['network_listen_ports'][name_temp]['listen_container_name'] = docker_temp['name']
                        inventory['network_listen_ports'][name_temp]['listen_container_image'] = docker_temp['image']
                        inventory['network_listen_ports'][name_temp]['listen_container_id'] = docker_temp['id']
            docker.append(docker_temp)
        
        inventory['docker_containers'] = docker

    ip_link_raw = readLINESfromFile('ip_link.txt')
    ip_addr_raw = readLINESfromFile('ip_addr.txt')

    for temp_str in ip_link_raw:
        temp_str_by_words = temp_str.split()
        if temp_str[0].isdigit():
            temp_link_data = None
            id = temp_str.replace(': ', ':').split(':')[1]
            if '@' in id:
                if id.split('@')[1] in inventory['network_interfaces'].keys():
                    temp_link_data = id.split('@')[1]
                id = id.split('@')[0]
            if id not in inventory['network_interfaces'].keys():
                inventory['network_interfaces'][id] = {}
            if temp_link_data is not None:
                inventory['network_interfaces'][id]['link'] = temp_link_data
            if 'master' in temp_str_by_words:
                inventory['network_interfaces'][id]['master'] = temp_str_by_words[temp_str_by_words.index('master')+1]
        if 'link/ether' in temp_str_by_words:
            inventory['network_interfaces'][id]['mac'] = temp_str_by_words[temp_str_by_words.index('link/ether')+1]
        if 'altname' in temp_str_by_words:
            if 'altnames' not in inventory['network_interfaces'][id].keys():
                inventory['network_interfaces'][id]['altnames'] = []
            inventory['network_interfaces'][id]['altnames'].append(temp_str_by_words[temp_str_by_words.index('altname')+1])

    for temp_str in ip_addr_raw:
        temp_str_by_words = temp_str.split()
        if temp_str[0].isdigit():
            id = temp_str.replace(': ', ':').split(':')[1]
            if '@' in id:
                id = id.split('@')[0]
        if 'inet' in temp_str_by_words:
            if 'ips' not in inventory['network_interfaces'][id].keys():
                inventory['network_interfaces'][id]['ips'] = []
            temp_ip4 = temp_str_by_words[temp_str_by_words.index('inet')+1]
            inventory['network_interfaces'][id]['ips'].append(temp_ip4)
            if id != 'lo':
                inventory['network_all_ip_addresses'].append(temp_ip4)
        elif 'inet6' in temp_str_by_words:
            if 'ips' not in inventory['network_interfaces'][id].keys():
                inventory['network_interfaces'][id]['ips'] = []
            temp_ip6 = temp_str_by_words[temp_str_by_words.index('inet6')+1]
            inventory['network_interfaces'][id]['ips'].append(temp_ip6)
            if id != 'lo':
                inventory['network_all_ip_addresses'].append(temp_ip6)
    
    raw_routes = readLINESfromFile('network_routes_all.txt')
    
    route_destination = None
    for line in raw_routes:
        l1 = line.split()
        if route_destination != l1[0]:
            t_route = {}
            k1 = True
        if not line.startswith('\t') and len(line) > 0:
            route_destination = l1[0]
            if route_destination not in inventory['network_routes_all'].keys():
                inventory['network_routes_all'][route_destination] = []
            if 'src' in l1:
                t_route['src'] = l1[l1.index('src') + 1]
            if 'via' in l1:
                t_route['gw'] = l1[l1.index('via') + 1]
            if 'dev' in l1:
                t_route['dev'] = l1[l1.index('dev') + 1]
        elif line.startswith('\t') and len(line) > 0 and 'nexthop' in line.lower():
            if 'src' in l1:
                t_route['src'] = l1[l1.index('src') + 1]
            if 'via' in l1:
                t_route['gw'] = l1[l1.index('via') + 1]
            if 'dev' in l1:
                t_route['dev'] = l1[l1.index('dev') + 1]
        if len(t_route) > 0:
            if 'dev' in t_route.keys():
                if t_route['dev'] in inventory['network_interfaces']:
                    if 'routes_to' not in inventory['network_interfaces'][t_route['dev']].keys():
                        inventory['network_interfaces'][t_route['dev']]['routes_to'] = []
                    inventory['network_interfaces'][t_route['dev']]['routes_to'].append(route_destination)
            if k1:
                inventory['network_routes_all'][route_destination].append(t_route)
                k1 = False

    inventory['network_all_ip_addresses'].sort()
    inventory['network_interfaces'].pop('lo')

    # NETWORK END
    # ----------------------------------------------------------------------
    # LSHW & LSPCI & STORCLI BEGIN

    parse_lshw_l0(readJSONfromFile('lshw.json'), inventory)

    if os.path.exists('storcli-controllers.txt'):
        t_controller = {}
        for line in readLINESfromFile('storcli-controllers.txt'):
            t1 = line.split('=')
            t_controller[t1[0].lower()] = t1[1]
        
        for controller in inventory['storages']:
            if 'megaraid' in controller['model'].lower():
                controller['model_by_storcli'] = t_controller['model']
                controller['serial'] = t_controller['serial number']

    if os.path.exists('storcli-disks.json'):
        parse_storcli_l0(readJSONfromFile('storcli-disks.json'), inventory)

    if os.path.exists('megacli-disks.txt'):
        temp_disk = {}
        for line in readLINESfromFile('megacli-disks.txt'):
            temp = line.split(':')
            if temp[0].lower() == 'wwn':
                temp_disk['wwn'] = temp[1].strip().upper()
            elif temp[0].lower() == 'raw size':
                temp_disk['size_raw'] = temp[1].strip()
            elif temp[0].lower() == 'inquiry data':
                t_line = temp[1].split()
                temp_disk['serial'] = t_line[0]
                temp_disk['fw_version'] = t_line[-1]
                temp_disk['model'] = ' '.join(t_line[1:-1:])
                inventory['disks'].append(temp_disk)
                temp_disk = {}
    
    if os.path.exists('megacli-controllers.txt'):
        t_controller = {}
        for line in readLINESfromFile('megacli-controllers.txt'):
            t1 = line.split(':')
            t_controller[t1[0].lower().strip()] = t1[1].strip()
        
        for controller in inventory['storages']:
            if 'megaraid' in controller['model'].lower():
                controller['model_by_storcli'] = t_controller['product name']
                controller['serial'] = t_controller['serial no']

    for line in readLINESfromFile('volumes.txt')[1::]:
        temp_volume = {}
        q = 1
        for rec in line.split():
            t1 = rec.split('=')
            temp_volume[t1[0].lower()] = t1[1] if len(t1[1]) > 0 else None
        if temp_volume['size'] is not None:
            if 'T' in temp_volume['size']:
                q = 2 ** 40
                t2 = temp_volume['size'].replace('T', '')
            elif 'G' in temp_volume['size']:
                q = 2 ** 30
                t2 = temp_volume['size'].replace('G', '')
            elif 'M' in temp_volume['size']:
                q = 2 ** 20
                t2 = temp_volume['size'].replace('M', '')
            elif 'K' in temp_volume['size']:
                q = 2 ** 10
                t2 = temp_volume['size'].replace('K', '')
            try:
                temp_volume['size_in_gb'] = int(float(t2) * q // GB)
            except:
                temp_volume['size_in_gb'] = None
        inventory['volumes'].append(temp_volume)

    #inventory['volumes']

    # LSHW & LSPCI & STORCLI  END
    # ----------------------------------------------------------------------
    # POSTRUN BEGIN

    inventory.pop('network_nonstd_id')
    for interface in inventory['network_interfaces'].values():
        if 'ips' in interface.keys():
            if len(interface['ips']) == 0:
                interface.pop('ips')

    # POSTRUN END
    # ----------------------------------------------------------------------
    # OUTPUT RESULTS BEGIN

    if to_screen == True:
        print(json.dumps(inventory, ensure_ascii='UTF-8', indent=4))

    if to_file == True:
        dumpJSONtoFile(filename, inventory)

    # OUTPUT RESULTS END
    # ----------------------------------------------------------------------

def main():
    inventory(to_screen=True, to_file=True, filename='result')

if __name__ == '__main__':
    main()
