#!/usr/bin/python3
"""Waybar JSON stream, stdlib only; one lightweight stream per output."""
from collections import deque
from functools import lru_cache
from pathlib import Path
import argparse
import html
import json
import os
import shutil
import subprocess
import time

BLUE='#89b4fa'; TEXT='#cdd6f4'; MUTED='#7f849c'; TEAL='#94e2d5'
PEACH='#fab387'; RED='#f38ba8'

def cpu_times():
    result={}
    for line in Path('/proc/stat').read_text().splitlines():
        if not line.startswith('cpu'):
            break
        fields=line.split();values=list(map(int,fields[1:9]))
        result[fields[0]]=(sum(values),values[3]+values[4])
    return result

def usage(before,after):
    total=after[0]-before[0];idle=after[1]-before[1]
    return max(0.0,min(100.0,100.0*(total-idle)/total)) if total>0 else 0.0

def cpu_temperature():
    for directory in Path('/sys/class/hwmon').glob('hwmon*'):
        try:
            name=(directory/'name').read_text().strip()
            if name not in ('k10temp','coretemp','zenpower'):
                continue
            candidates=[]
            for path in directory.glob('temp*_input'):
                labelpath=path.with_name(path.name.replace('_input','_label'))
                label=labelpath.read_text().strip() if labelpath.exists() else ''
                value=float(path.read_text())/1000
                if label in ('Tctl','Package id 0'):
                    return value
                candidates.append(value)
            if candidates:
                return max(candidates)
        except (OSError,ValueError):
            continue
    return None

def memory():
    values={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value=line.split(':',1);values[key]=int(value.split()[0])*1024
    total=values['MemTotal'];available=values['MemAvailable']
    return {'total':total,'used':total-available,'available':available,
            'swap_total':values['SwapTotal'], 'swap_used':values['SwapTotal']-values['SwapFree']}

def spark(values,low=0,high=100):
    values=list(values)
    if len(values)%2:
        values.insert(0,values[0])
    def level(v):
        return max(0,min(3,round((v-low)/(high-low)*3)))
    left=(6,2,1,0);right=(7,5,4,3)
    return ''.join(chr(0x2800|(1<<left[level(a)])|(1<<right[level(b)])) for a,b in zip(values[::2],values[1::2]))

def gpu_info():
    if not shutil.which('nvidia-smi'):
        return 'NVIDIA: nvidia-smi недоступен'
    try:
        result=subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total,power.draw',
            '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=2,check=True)
        load,temp,used,total,power=[x.strip() for x in result.stdout.splitlines()[0].split(',')]
        return f'NVIDIA GTX 1660 Super: {load}% · {temp}°C\nVRAM {used} / {total} MiB · {power} W'
    except (OSError,subprocess.SubprocessError,ValueError,IndexError):
        return 'NVIDIA: данные временно недоступны'

def span(text,color):
    return f'<span foreground="{color}">{html.escape(str(text))}</span>'

def severity(value, warning, critical):
    return 2 if value >= critical else 1 if value >= warning else 0


def metric_color(level, normal=TEXT):
    return RED if level == 2 else PEACH if level == 1 else normal


def disk_snapshot():
    result = {}
    for line in Path('/proc/diskstats').read_text().splitlines():
        fields = line.split()
        if len(fields) < 14:
            continue
        name = fields[2]
        block = Path('/sys/class/block') / name
        # Physical disks only: do not double-count their partitions or zram.
        if not (block / 'device').exists() or (block / 'partition').exists():
            continue
        result[name] = {'read': int(fields[5]) * 512, 'write': int(fields[9]) * 512,
                        'busy': int(fields[12])}
    return result


def disk_rates(previous, current, seconds):
    rates = {}
    for name, now in current.items():
        before = previous.get(name)
        if before is None or seconds <= 0:
            continue
        rates[name] = {'read': max(0, now['read'] - before['read']) / seconds,
                       'write': max(0, now['write'] - before['write']) / seconds,
                       'busy': max(0, min(100, (now['busy'] - before['busy']) / (seconds * 10)))}
    return rates


@lru_cache(maxsize=8)
def filesystem_identity(path):
    try:
        result = subprocess.run(['findmnt', '--json', '--target', path, '--output', 'SOURCE,FSTYPE'],
                                capture_output=True, text=True, timeout=2, check=True)
        fs = json.loads(result.stdout)['filesystems'][0]
        return (fs['source'].split('[')[0], fs['fstype'])
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
        return os.statvfs(path).f_fsid


def storage():
    groups = {}
    for path in ['/', str(Path.home())]:
        try:
            stat = os.statvfs(path)
            identity = filesystem_identity(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            if identity in groups:
                groups[identity]['paths'].append(path)
            else:
                groups[identity] = {'paths': [path], 'free': free, 'total': total,
                                    'level': severity(100 * (1 - free / total), 90, 95)}
        except OSError:
            continue
    return list(groups.values())


def payload(cpu,cores,temp,mem,history,temps,gpu,disks=None,filesystems=None):
    pct=mem['used']/mem['total']*100
    used=mem['used']/2**30;total=mem['total']/2**30
    filled=max(0,min(6,round(pct/100*6)))
    memlevel=severity(pct,80,90);cpulevel=severity(cpu,80,95)
    gauge=span('━'*filled,metric_color(memlevel,TEAL))+span('━'*(6-filled),MUTED)
    templevel=severity(temp,85,90) if temp is not None else 0
    tempcolor=metric_color(templevel)
    temperature=span(f'{temp:.0f}°C',tempcolor) if temp is not None else span('—°C',MUTED)
    text=f'{span("",BLUE)} CPU {span(f"{cpu:2.0f}%",metric_color(cpulevel))} {span(spark(history),metric_color(cpulevel,BLUE))} {temperature}  {span("│",MUTED)}  {span("",TEAL)} {span(f"{used:4.1f}/{total:.1f}G",metric_color(memlevel))} {gauge}'
    core_rows=[]
    for index in range(0,len(cores),2):
        core_rows.append('   '.join(f'{name}: {value:4.0f}%' for name,value in cores[index:index+2]))
    tooltip=f'<b>AMD Ryzen 7 5800X</b> · CPU {cpu:.1f}%\n'
    tooltip+='График: последние 60 секунд · обновление 2 с\n'
    if temp is not None:
        tooltip+=f'Tctl: {temp:.1f}°C'
        if temps:
            tooltip+=f' · мин. {min(temps):.1f} / макс. {max(temps):.1f}°C\n'+spark(temps,30,95)
        tooltip+='\n'
    tooltip+='\n'+'\n'.join(core_rows)
    tooltip+=f'\n\n<b>ОЗУ</b>: {used:.1f} / {total:.1f} GiB ({pct:.0f}%)\nДоступно: {mem["available"]/2**30:.1f} GiB\n'
    tooltip+=f'Swap: {mem["swap_used"]/2**30:.1f} / {mem["swap_total"]/2**30:.1f} GiB\n'
    filesystems = storage() if filesystems is None else filesystems
    disks = disks or {}
    tooltip+='\n<b>Место на диске</b>\n'
    for fs in filesystems:
        paths = ', '.join(fs['paths'])
        line = f"{paths}: свободно {fs['free']/2**30:.1f} / {fs['total']/2**30:.1f} GiB"
        tooltip += span(line, metric_color(fs['level'])) + '\n'
    tooltip+='\n<b>Дисковый ввод-вывод</b> · интервал 2 с\n'
    for name, rate in disks.items():
        line = f"{name}: R {rate['read']/2**20:.2f} MiB/s · W {rate['write']/2**20:.2f} MiB/s · занят {rate['busy']:.0f}%"
        tooltip += span(line, metric_color(severity(rate['busy'],80,95))) + '\n'
    if not disks:
        tooltip+='Нет данных о физических накопителях\n'
    tooltip+='Занятость — время активности устройства, не доля предельной скорости.\n'
    tooltip+=f'\n{html.escape(gpu)}\n\nНажатие: подробные графики в btop'
    level=max([cpulevel,memlevel,templevel]+[fs['level'] for fs in filesystems]+[severity(r['busy'],80,95) for r in disks.values()])
    return {'text':text,'tooltip':tooltip,'class':('normal','warning','critical')[level],'percentage':round(cpu)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    previous=cpu_times();history=deque(maxlen=30);temps=deque(maxlen=30);gpu='';next_gpu=0.0
    previous_disks=disk_snapshot();previous_time=time.monotonic()
    time.sleep(0.2)
    while True:
        tick=time.monotonic();current_disks=disk_snapshot()
        disks=disk_rates(previous_disks,current_disks,tick-previous_time)
        previous_disks=current_disks;previous_time=tick
        now=cpu_times();cpu=usage(previous['cpu'],now['cpu'])
        cores=[(key,usage(previous[key],value)) for key,value in now.items() if key!='cpu' and key in previous]
        previous=now;temp=cpu_temperature();history.append(cpu)
        if temp is not None:temps.append(temp)
        padded=[history[0]]*(30-len(history))+list(history)
        if time.monotonic()>=next_gpu:
            gpu=gpu_info();next_gpu=time.monotonic()+15
        print(json.dumps(payload(cpu,cores,temp,memory(),padded,list(temps),gpu,disks),ensure_ascii=False),flush=True)
        if args.once:break
        time.sleep(2)

if __name__=='__main__':
    try:main()
    except (BrokenPipeError,KeyboardInterrupt):pass
