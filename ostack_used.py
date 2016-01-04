#!/usr/bin/env python
#

import os
import sys
import subprocess
import re
import requests
import argparse

def exec_cmd(cmd, verbose=True):
    result = []
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(out.stdout.readline, b''):
        if verbose:
            print(line.rstrip())
        result.append(line.strip())
    return result

def build_hyplist(azone):
    svclist = exec_cmd(nova_cmd + ['service-list'], verbose=False)
    services = []
    computes = []
    if azone == 'nova':
        pattern = '^.*nova-compute.*$'
    else:
        pattern = '^.*nova-compute.*' + azone + ' .*$'
    for line in svclist:
        if re.search(pattern, line):
            services.append(line.split()[3])
    hyplist = exec_cmd(nova_cmd + ['hypervisor-list'], verbose=False)
    for i in services:
        for line in hyplist:
            if re.search(i, line):
                computes.append(line.split()[3])
    computes.sort()
    return computes

def env_use(ratios):
    hypstats = exec_cmd(nova_cmd + ['hypervisor-stats'], verbose=False)
    USAGE_VARS = ['HYP_COUNT', 'DISK_AVAIL', 'DISK_TOTAL', 'DISK_USED', 'RAM_TOTAL', 'RAM_USED', 'VCPUS_TOTAL', 'VCPUS_USED']
    USAGE_REGEX = ['count', 'disk_available_least', 'local_gb ', 'local_gb_used', 'memory_mb ', 'memory_mb_used', 'vcpus ', 'vcpus_used']
    USAGE_VALS = []
    for line in hypstats:
        for i in USAGE_REGEX:
            if re.search(i, line):
                USAGE_VALS.append(float(line.split()[3]))
    USAGE = dict(zip(USAGE_VARS, USAGE_VALS))
    print('\n-= Overall Environment Resource Utilization =-\n')
    print("Hypervisors in Environment : %d" % (USAGE['HYP_COUNT']))
    print
    print("Total Disk in Environment : %s GB" % (USAGE['DISK_TOTAL']))
    print("Disk in Use : %s GB" % (USAGE['DISK_USED']))
    print("Calculated Disk Available : %s GB" % (USAGE['DISK_AVAIL']))
    print("Percent of Disk Used : %.2f %%" % (((USAGE['DISK_TOTAL'] - USAGE['DISK_AVAIL']) / (USAGE['DISK_TOTAL'] * ratios[1])) * 100 ))
    print
    print("Total RAM in Environment : %s GB" % (USAGE['RAM_TOTAL']))
    print("RAM in Use : %s GB" % (USAGE['RAM_USED']))
    print("Percent of RAM Used : %.2f %%" % ((USAGE['RAM_USED'] / (USAGE['RAM_TOTAL'] * ratios[2])) * 100 ))
    print
    print("Total vCPUs in Environment : %d" % (USAGE['VCPUS_TOTAL']))
    print("vCPUs in Use : %d" % (USAGE['VCPUS_USED']))
    print("Percent of vCPUs Used : %.2f %%" % ((USAGE['VCPUS_USED'] / (USAGE['VCPUS_TOTAL'] * ratios[0])) * 100 ))
    print
    print("CPU Allocation Ratio : %s\nDisk Allocation Ratio : %s\nRAM Allocation Ratio : %s\n" % (ratios[0], ratios[1], ratios[2]))

def zone_use(USAGE, numhyps, ratios):
    print('\n-= Availability Zone Usage =-\n')
    print("Hypervisors in Zone %s : %d" % (args.zone, numhyps))
    print
    print("Total Disk in Zone %s : %s GB" % (args.zone, USAGE['DISK_TOTAL']))
    print("Disk in Use : %s GB" % (USAGE['DISK_USED']))
    print("Calculated Disk Available : %s GB" % (USAGE['DISK_AVAIL']))
    print("Percent of Disk Used : %.2f %%" % (((USAGE['DISK_TOTAL'] - USAGE['DISK_AVAIL']) / (USAGE['DISK_TOTAL'] * ratios[1])) * 100 ))
    print
    print("Total RAM in Zone %s : %s GB" % (args.zone, USAGE['RAM_TOTAL']))
    print("RAM in Use : %s GB" % (USAGE['RAM_USED']))
    print("Percent of RAM Used : %.2f %%" % ((USAGE['RAM_USED'] / (USAGE['RAM_TOTAL'] * ratios[2])) * 100 ))
    print
    print("Total vCPUs in Zone %s : %d" % (args.zone, USAGE['VCPUS_TOTAL']))
    print("vCPUs in Use : %d" % (USAGE['VCPUS_USED']))
    print("Percent of vCPUs Used : %.2f %%" % ((USAGE['VCPUS_USED'] / (USAGE['VCPUS_TOTAL'] * ratios[0])) * 100 ))
    print
    print("CPU Allocation Ratio : %s\nDisk Allocation Ratio : %s\nRAM Allocation Ratio : %s\n" % (ratios[0], ratios[1], ratios[2]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpu', help='CPU Allocation Ratio', action='store', type=float)
    parser.add_argument('--disk', help='Disk Allocation Ratio', action='store', type=float)
    parser.add_argument('--ram', help='RAM Allocation Ratio', action='store', type=float)
    parser.add_argument('--zone', help='Availability Zone', action='store', default='nova', type=str)
    args = parser.parse_args()

    ALLOCATION_RATIOS = []
    if not args.cpu or not args.disk or not args.ram:
        print('Resource allocation ratios required. Use --help for usage.')
        sys.exit(1)
    else:
        for i in [args.cpu, args.disk, args.ram]:
            ALLOCATION_RATIOS.append(i)

    PARAMS = ['OS_ENDPOINT_TYPE', 'OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME', 'OS_AUTH_URL']
    ENV_PARAMS = []
    for i in PARAMS:
        try:
            ENV_PARAMS.append(os.environ[i])
        except:
            print('Environment variable %s not set' % (i))
            sys.exit(1)
    NOVA_PARAMS = dict(zip(PARAMS, ENV_PARAMS))

    nova_cmd = ['nova', '--endpoint-type', NOVA_PARAMS['OS_ENDPOINT_TYPE'], '--os-username', NOVA_PARAMS['OS_USERNAME'], '--os-password', NOVA_PARAMS['OS_PASSWORD'], '--os-tenant-name', NOVA_PARAMS['OS_TENANT_NAME'], '--os-auth-url', NOVA_PARAMS['OS_AUTH_URL']]

    hypervisors = build_hyplist(args.zone)

    PER_HYP = []
    for i in hypervisors:
        PER_HYP.append(exec_cmd(nova_cmd + ['hypervisor-show', i], verbose=False))

    PER_USAGE_VARS = ['DISK_AVAIL', 'DISK_TOTAL', 'DISK_USED', 'RAM_TOTAL', 'RAM_USED', 'RUNNING_VMS', 'VCPUS_TOTAL', 'VCPUS_USED']
    PER_USAGE_REGEX = ['disk_available_least', 'local_gb ', 'local_gb_used', 'memory_mb ', 'memory_mb_used', 'running_vms', 'vcpus ', 'vcpus_used']
    TOTALS = {el:0 for el in PER_USAGE_VARS}

    hypnum = 0
    for hyp in PER_HYP:
        PER_USAGE_VALS = []
        for line in hyp:
            for i in PER_USAGE_REGEX:
                if re.search(i, line):
                    PER_USAGE_VALS.append(float(line.split()[3]))
        PER_USAGE = dict(zip(PER_USAGE_VARS, PER_USAGE_VALS))
        print("--== %s ==--" % (hypervisors[hypnum]))
        print("Disk : %s GB" % (PER_USAGE['DISK_TOTAL']))
        print("Disk in Use : %s GB" % (PER_USAGE['DISK_USED']))
        print("Calculated Disk Available : %s GB" % (PER_USAGE['DISK_AVAIL']))
        print
        print("RAM : %s GB" % (PER_USAGE['RAM_TOTAL']))
        print("RAM in Use : %s GB" % (PER_USAGE['RAM_USED']))
        print
        print("Total vCPUs : %d" % (PER_USAGE['VCPUS_TOTAL']))
        print("vCPUs in Use : %d" % (PER_USAGE['VCPUS_USED']))
        print
        print("Percent of Disk Used : %.2f %%" % (((PER_USAGE['DISK_TOTAL'] - PER_USAGE['DISK_AVAIL']) / (PER_USAGE['DISK_TOTAL'] * ALLOCATION_RATIOS[1])) * 100 ))
        print("Percent of RAM Used : %.2f %%" % ((PER_USAGE['RAM_USED'] / (PER_USAGE['RAM_TOTAL'] * ALLOCATION_RATIOS[2])) * 100 ))
        print("Percent of vCPUs Used : %.2f %%" % ((PER_USAGE['VCPUS_USED'] / (PER_USAGE['VCPUS_TOTAL'] * ALLOCATION_RATIOS[0])) * 100 ))
        print("--------------------------------")
        TOTALS['DISK_TOTAL'] += PER_USAGE['DISK_TOTAL']
        TOTALS['DISK_USED'] += PER_USAGE['DISK_USED']
        TOTALS['DISK_AVAIL'] += PER_USAGE['DISK_AVAIL']
        TOTALS['RAM_TOTAL'] += PER_USAGE['RAM_TOTAL']
        TOTALS['RAM_USED'] += PER_USAGE['RAM_USED']
        TOTALS['VCPUS_TOTAL'] += PER_USAGE['VCPUS_TOTAL']
        TOTALS['VCPUS_USED'] += PER_USAGE['VCPUS_USED']
        hypnum += 1

    if args.zone == 'nova':
        env_use(ALLOCATION_RATIOS)
    else:
        zone_use(TOTALS, hypnum, ALLOCATION_RATIOS)
