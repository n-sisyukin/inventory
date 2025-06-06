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

start_dir=$(dirname ${0})
if [ "$start_dir" = "." ]; then
    start_dir=$(pwd)
fi

logfile=$start_dir/inventory2.log
rm -f $logfile
touch $logfile

blockfile=$start_dir/blockfile.lock
if [[ -f $blockfile ]]; then
    echo "Script is already running. Exiting."
    exit 1
fi
touch $blockfile

inventory_script_version="VERSION"
inventory_script_version_path=$start_dir/$inventory_script_version
inventory_script_file="inventory2.py"
inventory_script_file_path=$start_dir/$inventory_script_file

for file in $(ls -la $start_dir | awk '{print $NF}' | grep -i result); do
    rm -f $file
done

temp_path=/tmp
inventory_subdir=inventory-$(date +"%Y-%m-%d")
full_work_path=$temp_path/$inventory_subdir

if [[ ! -d ${full_work_path} ]]; then
  mkdir -p ${full_work_path}
fi

cp -f $inventory_script_version_path $full_work_path
cp -f $inventory_script_file_path $full_work_path
cd $full_work_path

inventory_script_file_path=$full_work_path/$inventory_script_file

date +"%Y-%m-%d | %H:%M" > date_of_inventory.txt
lshw -json > lshw.json
hostname > os_hostname.txt
grep -i pretty /etc/os-release | awk -F\" '{print $2}' > os_version.txt
uname -r > os_core.txt
awk -F: '{print $1}' /etc/passwd | grep -iv nobody > os_users.txt
cat /etc/group | grep -i sudo | awk -F":" '{print $NF}' > os_users_sudo.txt
cat /etc/group | grep -i wheel | awk -F":" '{print $NF}' > os_users_wheel.txt
grep "Port " /etc/ssh/sshd_config | awk '{print $NF}' > os_ssh_port.txt
cat /etc/ssh/sshd_config | grep -i allowusers | cut -d' ' -f2- > os_users_ssh.txt
openssl version > os_ssl_version.txt
ssh -V > os_ssh_version.txt 2>&1

if (command -v docker &>>$logfile) && (docker ps &>>$logfile); then
    docker ps --no-trunc --format '{{json .}}' | jq -s | sed 's/\\\"//g' | jq > docker.json
fi

netstat -tulpen | grep -e 'tcp' -e 'udp' > netstat.txt
ip link > ip_link.txt
ip addr > ip_addr.txt
ip route | sed -e 's/scope link //g' -e 's/proto //g' -e 's/ linkdown//g' -e 's/ kernel//g' -e 's/ static//g' > network_routes_all.txt

lsblk -a -P -p -o NAME,FSTYPE,MOUNTPOINT,SIZE,TYPE | grep -iv loop | sed 's/\"//g'> volumes.txt

if test -f "/usr/local/bin/MegaCli"; then
    megacli="/usr/local/bin/MegaCli";
    $megacli -AdpAllInfo -aALL -NoLog | grep -i -e "Product Name" -e "Serial No" > megacli-controllers.txt;
    $megacli -PDList -aAll -NoLog | grep -i -e "wwn" -e "inquiry" -e "Raw Size" > megacli-disks.txt;
elif test -f "/opt/MegaRAID/storcli/storcli64"; then
    storcli="/opt/MegaRAID/storcli/storcli64";
    $storcli \/call show all nolog | grep -i -e "model = " -e "serial number = " -e "pci address" | grep -iv support | sed 's/ = /=/g' > storcli-controllers.txt;
    $storcli \/call \/eall \/sall show all J nolog > storcli-disks.json;
elif test -f "/opt/MegaRAID/storcli/storcli"; then
    storcli="/opt/MegaRAID/storcli/storcli";
    $storcli \/call show all nolog | grep -i -e "model = " -e "serial number = " -e "pci address" | grep -iv support | sed 's/ = /=/g' > storcli-controllers.txt;
    $storcli \/call \/eall \/sall show all J nolog > storcli-disks.json;
fi

if command -v apt &>>$logfile; then
    apt --installed list > packages_apt.txt 2>>$logfile
elif command -v yum &>>$logfile; then
    yum list installed > packages_yum.txt 2>>$logfile
fi

if command -v python3 &>>$logfile; then
    python3 $inventory_script_file_path 2>>$logfile
else
    python $inventory_script_file_path 2>>$logfile
fi

for file in $(ls -la $full_work_path | awk '{print $NF}' | grep -i result); do
    cp -f $file $start_dir
done

cd $start_dir
rm -rf $full_work_path
rm -f $blockfile