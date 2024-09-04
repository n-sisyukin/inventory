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

import json, subprocess, sys

def readJSONfromFile(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        return json.load(f)

def dumpJSONtoFile(filename, data, mode='w'):
    if data != None:
        with open(filename, mode, encoding="UTF-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    return

def assing_if_is(value, key):
    if key in value.keys():
        if value[key] != 'None':
            return value[key]
        else:
            return None
    else:
        return None

def inventory(to_screen=True, to_file=True, filename='inventory_result.json'):
    lshw_full = json.loads(subprocess.run(['lshw', '-json'], capture_output=True, text=True).stdout)

    inventory = {}
    
    # ----------------------------------------------------------------------

    # OS BEGIN
    
    inventory['is_vm'] = False

    inventory['os_hostname'] = subprocess.run(['hostname'], capture_output=True, text=True).stdout.split()[0]
    inventory['os_version'] = subprocess.run(['grep', '-i', 'pretty', '/etc/os-release'], capture_output=True, text=True).stdout.split("\"")[1]
    inventory['os_core'] = subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.split()[0]
    inventory['os_users'] = [user.split(':')[0] 
                             for user in subprocess.run(['cat', '/etc/passwd'], capture_output=True, text=True).stdout.split('\n')[:-1:] 
                             if 1000 <= int(user.split(':')[2]) < 60000]
    inventory['os_users'].sort()
    
    # OS END

    # ----------------------------------------------------------------------
    
    # SYSTEM BEGIN

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'system'], capture_output=True, text=True).stdout)
    
    inventory['system_vendor'] = lshw_temp[0]['vendor']
    inventory['system_platform'] = lshw_temp[0]['product']
    if 'serial' in lshw_temp[0].keys():
        inventory['system_serial'] = lshw_temp[0]['serial']
    
    if 'vmware' in inventory['system_platform'].lower() or 'kvm' in inventory['system_platform'].lower():
        inventory['is_vm'] = True

    # SYSTEM END

    # ----------------------------------------------------------------------
    
    # CPU BEGIN

    inventory['cpu_model'] = None
    inventory['cpu_count'] = 0
    inventory['cpu_count_of_all_cores'] = 0
    inventory['cpu_count_of_all_threads'] = 0

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'cpu'], capture_output=True, text=True).stdout)

    for temp in lshw_temp:
        if 'product' in temp.keys():
            inventory['cpu_model'] = temp['product']
            inventory['cpu_count'] += 1
            inventory['cpu_count_of_all_cores'] += int(temp['configuration']['cores'])
            inventory['cpu_count_of_all_threads'] += int(temp['configuration']['threads']) if 'threads' in temp['configuration'] else int(temp['configuration']['cores'])
    
    # CPU END

    # ----------------------------------------------------------------------

    # MOTHERBOARD BEGIN

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'bus'], capture_output=True, text=True).stdout)

    for temp in lshw_temp:
        if 'description' in temp.keys():
            if temp['description'] == 'Motherboard':
                inventory['mb_vendor'] = assing_if_is(temp, 'vendor')
                inventory['mb_model'] = assing_if_is(temp, 'product')
                inventory['mb_version'] = assing_if_is(temp, 'version')
                inventory['mb_serial'] = assing_if_is(temp, 'serial')

    inventory['mb_bios_vendor'] = assing_if_is(lshw_full['children'][0]['children'][0], 'vendor')
    inventory['mb_bios_version'] = assing_if_is(lshw_full['children'][0]['children'][0], 'version')
    inventory['mb_bios_date'] = assing_if_is(lshw_full['children'][0]['children'][0], 'date')

    # MOTHERBOARD END

    # ----------------------------------------------------------------------
    
    # VGA BEGIN

    inventory['vga'] = []

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'video'], capture_output=True, text=True).stdout)

    for temp in lshw_temp:
        vga = {}
        vga['vga_vendor'] = assing_if_is(temp, 'vendor')
        vga['vga_model'] = assing_if_is(temp, 'product')
        inventory['vga'].append(vga)


    # VGA END

    # ----------------------------------------------------------------------

    # POWER BEGIN

    inventory['psu_count'] = 0
    inventory['psu'] = []

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'power'], capture_output=True, text=True).stdout)

    for temp in lshw_temp:
        power = {}
        power['vendor'] = assing_if_is(temp, 'vendor')
        power['model'] = assing_if_is(temp, 'product')
        power['serial'] = assing_if_is(temp, 'serial')
        power['capacity'] = assing_if_is(temp, 'capacity')
        
        inventory['psu_count'] += 1
        inventory['psu'].append(power)
    
    # POWER END

    # ----------------------------------------------------------------------

    inventory['storage'] = []

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'storage'], capture_output=True, text=True).stdout)

    for temp in lshw_temp:
        if 'id' in temp.keys():
            storage = {}
            storage['vendor'] = assing_if_is(temp, 'vendor')
            storage['model'] = assing_if_is(temp, 'product')
            storage['serial'] = assing_if_is(temp, 'serial')
            
            inventory['storage'].append(storage)
    
    # ----------------------------------------------------------------------
    
    # DISK BEGIN
    
    inventory['disks'] = []

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'disk'], capture_output=True, text=True).stdout)

    for temp in lshw_temp:
        disk = {}
        disk['model'] = assing_if_is(temp, 'product')
        disk['size_in_gb'] = assing_if_is(temp, 'size')
        if isinstance(disk['size_in_gb'], int):
            disk['size_in_gb'] //= GB
        disk['serial'] = assing_if_is(temp, 'serial')
        disk['fw_version'] = assing_if_is(temp, 'version')
        disk['logicalname'] = assing_if_is(temp, 'logicalname')

        inventory['disks'].append(disk)
    
    # DISK END

    # ----------------------------------------------------------------------
    
    inventory['volumes'] = []#subprocess.run(['lsblk', '-P'], capture_output=True, text=True).stdout.split('\n')
    
    # ----------------------------------------------------------------------

    # MEMORY BEGIN

    inventory['memory_size_in_gb'] = None
    inventory['memory_modules_count'] = 0
    inventory['memory_modules'] = []

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'memory'], capture_output=True, text=True).stdout)

    for temp in lshw_temp:
        if temp['description'] == 'System Memory':
            inventory['memory_size_in_gb'] = temp['size'] / GB
        if 'size' in temp.keys() and 'slot' in temp.keys() and 'cache' not in temp['description'] and temp['description'] != 'System Memory':
            module = {}
            module['slot'] = temp['slot']
            module['vendor'] = assing_if_is(temp, 'vendor')
            module['model'] = assing_if_is(temp, 'product')
            module['type'] = temp['description']
            module['frequency_in_mhz'] = assing_if_is(temp, 'clock')
            if isinstance(module['frequency_in_mhz'], int):
                module['frequency_in_mhz'] //= 1000000
            module['serial'] = assing_if_is(temp, 'serial')
            module['size_in_gb'] = temp['size'] / GB

            inventory['memory_modules_count'] += 1
            inventory['memory_modules'].append(module)
    
    # MEMORY END
    
    # ----------------------------------------------------------------------

    # NETWORK BEGIN

    inventory['network_all_ip_addresses'] = []
    
    inventory['network_interfaces'] = {t_str.split()[0]: {'mac':t_str.split()[2]} for t_str in subprocess.run(['ip', '-br', 'link'], capture_output=True, text=True).stdout.split('\n')[:-1:]}
    
    for key, val in {t_str.split()[0]: {'ip': t_str.split()[2::]} for t_str in subprocess.run(['ip', '-br', 'addr'], capture_output=True, text=True).stdout.split('\n')[:-1:]}.items():
        if key in inventory['network_interfaces'].keys():
            inventory['network_interfaces'][key].update(val)
        else:
            inventory['network_interfaces'].update({key: val})
    
    inventory['network_interfaces'].pop('lo')

    for interface in inventory['network_interfaces'].values():
        for ip in interface['ip']:
            inventory['network_all_ip_addresses'].append(ip)
    
    inventory['network_all_ip_addresses'].sort()

    lshw_temp = json.loads(subprocess.run(['lshw', '-json', '-class', 'network'], capture_output=True, text=True).stdout)

    num_of_non_standart_intarface = 0
    for temp in lshw_temp:
        if 'logicalname' in temp.keys():
            if temp['logicalname'] not in inventory['network_interfaces'].keys():
                inventory['network_interfaces'][temp['logicalname']] = {}
            inventory['network_interfaces'][temp['logicalname']]['vendor'] = assing_if_is(temp, 'vendor')
            inventory['network_interfaces'][temp['logicalname']]['model'] = assing_if_is(temp, 'product')
        else:
            inventory['network_interfaces'][f"{temp['configuration']['driver']}{str(num_of_non_standart_intarface)}"] = {}
            inventory['network_interfaces'][f"{temp['configuration']['driver']}{str(num_of_non_standart_intarface)}"]['vendor'] = assing_if_is(temp, 'vendor')
            inventory['network_interfaces'][f"{temp['configuration']['driver']}{str(num_of_non_standart_intarface)}"]['model'] = assing_if_is(temp, 'product')
            num_of_non_standart_intarface += 1

    # NETWORK END

    # ----------------------------------------------------------------------
    
    # OUTPUT RESULTS BEGIN

    if to_screen == True:
        print(json.dumps(inventory, ensure_ascii='UTF-8', indent=4))
    
    if to_file == True:
        dumpJSONtoFile(filename, inventory)

    # OUTPUT RESULTS END

    # ----------------------------------------------------------------------

def main():
    inventory()

if __name__ == '__main__':
    main()
