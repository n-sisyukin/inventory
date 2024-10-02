#!/usr/bin/env bash

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

start_dir=$(pwd)
inventory_script_file="inventory2.py"
inventory_result_file="inventory_result.json"
inventory_script_file_path=$start_dir/$inventory_script_file

temp_path=/tmp
inventory_subdir=inventory-$(date +"%Y-%m-%d")
full_work_path=$temp_path/$inventory_subdir

mkdir $full_work_path
cp -f $inventory_script_file_path $full_work_path
cd $full_work_path

inventory_script_file_path=$full_work_path/$inventory_script_file
inventory_result_file_path=$full_work_path/$inventory_result_file

date +"%Y-%m-%d | %H:%M" > date_of_inventory.txt
lshw -json > lshw.json
hostname > os_hostname.txt
grep -i pretty /etc/os-release | awk -F\" '{print $2}' > os_version.txt
uname -r > os_core.txt
awk -F: '$3>=1000{print $1}' /etc/passwd | grep -iv nobody > os_users.txt
grep "Port " /etc/ssh/sshd_config | awk '{print $NF}' > os_ssh_port.txt
openssl version > os_ssl_version.txt
ssh -V 2> os_ssh_version.txt

netstat -tulpen | grep -e 'tcp' -e 'udp' > netstat.txt
ip link > ip_link.txt
ip addr > ip_addr.txt
ip route | sed 's/scope link //g' | sed 's/proto //g' | sed 's/ linkdown//g' | sed 's/ kernel//g' | sed 's/ static//g' > network_routes_all.txt

if test -f "/opt/MegaRAID/storcli/storcli64"; then
    storcli="/opt/MegaRAID/storcli/storcli64";
    $storcli \/call \/eall \/sall show all J > storcli.json;
fi
if test -f "/opt/MegaRAID/storcli/storcli"; then
    storcli="/opt/MegaRAID/storcli/storcli";
    $storcli \/call \/eall \/sall show all J > storcli.json;
fi

python $inventory_script_file_path 2> /dev/null
python3 $inventory_script_file_path 2> /dev/null

cp -f $inventory_result_file_path $start_dir

rm -rf $full_work_path