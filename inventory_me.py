#!/usr/bin/env python3

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

import json, subprocess, sys, os, ipaddress

# ----------------------------------------------------------------------

def readJSONfromFile(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        return json.load(f)

# ----------------------------------------------------------------------

def dumpJSONtoFile(filename, data, mode='w'):
    if data != None:
        with open(filename, mode, encoding="UTF-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    return

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
            inventory['os_hostname'] = lshw_data['id']
            inventory['system_vendor'] = assing_if_is(lshw_data, 'vendor')
            inventory['system_platform'] = assing_if_is(lshw_data, 'product')
            inventory['system_platform_version'] = assing_if_is(lshw_data, 'version')
            inventory['system_serial'] = assing_if_is(lshw_data, 'serial')
            if ('kvm' in inventory['system_platform'].lower() or
                'vmware' in inventory['system_platform'].lower()):
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
            inventory['cpu_count_of_all_cores'] += int(lshw_data['configuration']['cores'])
        
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
        
        if lshw_data['class'].lower() == 'disk':
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
        
        if lshw_data['class'].lower() == 'storage':
            temp_storage = {}
            temp_storage['vendor'] = assing_if_is(lshw_data, 'vendor')
            temp_storage['model'] = assing_if_is(lshw_data, 'product')
            temp_storage['serial'] = assing_if_is(lshw_data, 'serial')    
            inventory['storages'].append(temp_storage)

        if (lshw_data['class'].lower() == 'network' and
            'logicalname' in lshw_data.keys()):
            if lshw_data['logicalname'] in inventory['network_interfaces'].keys():
                if 'vendor' in lshw_data.keys():
                    inventory['network_interfaces'][lshw_data['logicalname']]['vendor'] = lshw_data['vendor']
                if 'product' in lshw_data.keys():
                    inventory['network_interfaces'][lshw_data['logicalname']]['product'] = lshw_data['product']

        elif (lshw_data['class'].lower() == 'network' and
              'logicalname' not in lshw_data.keys()):
            
            temp_id = f"{lshw_data['configuration']['driver']}{inventory['network_nonstd_id']}"
            inventory['network_interfaces'][temp_id] = {}
            if 'vendor' in lshw_data.keys():
                inventory['network_interfaces'][temp_id]['vendor'] = lshw_data['vendor']
            if 'product' in lshw_data.keys():
                inventory['network_interfaces'][temp_id]['product'] = lshw_data['product']
            inventory['network_nonstd_id'] += 1

# ----------------------------------------------------------------------

def inventory(to_screen=True, to_file=True, filename='inventory_result.json'):
    
    # ----------------------------------------------------------------------
    # PRERUN BEGIN

    inventory = {}

    inventory['is_vm'] = False

    inventory['os_hostname'] = None
    inventory['os_version'] = None
    inventory['os_core'] = None
    inventory['os_ssh_port'] = None
    inventory['os_listen_ports'] = {}
    inventory['os_users'] = []

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
    inventory['network_interfaces'] = {}
    inventory['network_nonstd_id'] = 0

    # PRERUN END
    # ----------------------------------------------------------------------
    # OS BEGIN

    inventory['os_version'] = subprocess.run(['grep', '-i', 'pretty', '/etc/os-release'], 
                                             capture_output=True, text=True
                                             ).stdout.split("\"")[1]
    inventory['os_core'] = subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.split()[0]
    
    inventory['os_users'] = [user.split(':')[0] 
                             for user in subprocess.run(['cat', '/etc/passwd'], 
                                                        capture_output=True, text=True
                                                        ).stdout.split('\n')[:-1:] 
                             if 1000 <= int(user.split(':')[2]) < 60000]
    inventory['os_users'].sort()
    
    netstat = [record.split() for record in subprocess.run(['netstat', '-tulpen'], 
                                                           capture_output=True, text=True
                                                           ).stdout.split('\n')[2:-1:]]
    #inventory['os_listen_ports'] = {f'{rec[0]}|{rec[3]}': f'{rec[-1]}' for rec in netstat}

    inventory['os_listen_ports'] = dict(
        sorted(
            {f"{rec[3].split(':')[-1]}|{rec[0]}|{':'.join(rec[3].split(':')[:-1:])}": 
             f"{rec[-1]}"
             #f"{rec[-1].split('/')[-1] if '/' in rec[-1] else rec[-1]}" 
             for rec in netstat
             }.items(), 
             key=lambda item: int(item[0].split('|')[0])))
    

    #for record in netstat:
        



    inventory['os_ssh_port'] = subprocess.run(['grep', '-i', 'port', '/etc/ssh/sshd_config'], 
                                              capture_output=True, text=True
                                              ).stdout.split('\n')[0].split()[1]
    
    # OS END
    # ----------------------------------------------------------------------
    # NETWORK BEGIN

    for link in json.loads(subprocess.run(['ip', '-j', 'link'], capture_output=True, text=True).stdout):
        inventory['network_interfaces'][link['ifname']] = {}
        if 'address' in link.keys():
            inventory['network_interfaces'][link['ifname']]['mac'] = link['address']
        if 'altnames' in link.keys():
            inventory['network_interfaces'][link['ifname']]['altnames'] = link['altnames']
        if 'master' in link.keys():
            inventory['network_interfaces'][link['ifname']]['master'] = link['master']
        if 'link' in link.keys():
            inventory['network_interfaces'][link['ifname']]['link'] = link['link']

    for link in json.loads(subprocess.run(['ip', '-j', 'addr'], capture_output=True, text=True).stdout):
        if link['ifname'] in inventory['network_interfaces'].keys():
            if 'addr_info' in link.keys():
                inventory['network_interfaces'][link['ifname']]['ips'] = []
                for addr in link['addr_info']:
                    temp_ip = f"{addr['local']}/{addr['prefixlen']}"
                    inventory['network_interfaces'][link['ifname']]['ips'].append(temp_ip)
                    if link['ifname'] != 'lo':
                        inventory['network_all_ip_addresses'].append(temp_ip)
    
    inventory['network_all_ip_addresses'].sort()
    inventory['network_interfaces'].pop('lo')

    # NETWORK END
    # ----------------------------------------------------------------------
    # LSHW BEGIN

    parse_lshw_l0(json.loads(subprocess.run(['lshw', '-json'], capture_output=True, text=True).stdout), inventory)

    # LSHW END
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
    inventory(to_screen=True, to_file=True, filename='inventory_result.json')

if __name__ == '__main__':
    main()