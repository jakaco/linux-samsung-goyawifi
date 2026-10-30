#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check Wi-Fi transfers while BlueZ discovery runs, using USB as control."""
import argparse,hashlib,json,re,socket,threading,time
from pathlib import Path
import paramiko

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--usb-host',required=True)
p.add_argument('--wifi-host',required=True)
p.add_argument('--host-key-name',required=True,help='Pinned known_hosts alias shared by both interfaces')
p.add_argument('--known-hosts',required=True,type=Path)
p.add_argument('--identity',required=True,type=Path)
p.add_argument('--user',default='root')
p.add_argument('--rounds',type=int,default=3)
p.add_argument('--mib',type=int,default=16)
p.add_argument('--scan-seconds',type=int,default=60,help='0 disables discovery; Bluetooth remains powered')
p.add_argument('--scan-transport',choices=['auto','bredr','le'],default='auto')
p.add_argument('--peer',help='Optional already-paired, explicitly selected Bluetooth peer for 60 44-byte L2CAP echoes')
p.add_argument('--output',required=True,type=Path)
a=p.parse_args()
assert 1<=a.rounds<=20 and 1<=a.mib<=64 and 0<=a.scan_seconds<=120
if a.peer and not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',a.peer):p.error('Invalid Bluetooth peer address')

def connect(address):
 c=paramiko.SSHClient();c.load_host_keys(str(a.known_hosts))
 try:
  c.connect(a.host_key_name,username=a.user,key_filename=str(a.identity),look_for_keys=False,allow_agent=False,timeout=30,banner_timeout=30,auth_timeout=30,sock=socket.create_connection((address,22),10))
 except Exception:
  c.close();raise
 return c

def command(c,text):
 _,o,e=c.exec_command(text,timeout=30);result=o.read().decode(errors='replace')
 if o.channel.recv_exit_status()!=0:raise RuntimeError('Control command failed')
 return result

control=connect(a.usb_host)
size=a.mib*1024*1024;payload=bytes(range(256))*(size//256)
report={'kernel':command(control,'uname -r').strip(),'bytes_per_direction_per_round':size,'scan_seconds':a.scan_seconds,'scan_transport':a.scan_transport,'rounds':[]}
report['kernel_build']=command(control,'uname -v').strip()
report['bluetooth_auto_sleep']=command(control,'cat /sys/kernel/debug/bluetooth/hci*/status/curpsmode 2>/dev/null || true').strip()
report['firmware']=command(control,'cat /sys/kernel/debug/mwifiex/*/verext 2>/dev/null || true').strip()
report['taint_before']=command(control,'cat /proc/sys/kernel/tainted').strip()
before=command(control,'dmesg')
data=None;timer=None;stage='start';peer=None
try:
 if a.peer:
  stage='paired peer sanity'
  # 44 payload bytes + 4 signaling-header bytes fit the minimum 48-byte
  # signaling MTU. Larger raw echoes can elicit kernel Command Rejects even
  # when l2ping receives a valid response; do not confuse that with RF loss.
  sanity=command(control,'timeout 10 /usr/sbin/l2ping -v -c 1 -s 44 -t 2 '+a.peer)
  if '1 sent, 1 received' not in sanity:raise RuntimeError('Peer echo unavailable')
  time.sleep(2)
  peer=control.exec_command('timeout 120 /usr/sbin/l2ping -v -c 60 -s 44 -t 2 '+a.peer,timeout=130)
  report['paired_peer_payload_bytes']=44
 if a.scan_seconds:
  mode='on' if a.scan_transport=='auto' else a.scan_transport
  # Keep these channel objects alive. BlueZ itself bounds discovery if the
  # test is interrupted; no daemon or permanent desktop policy is installed.
  scan=control.exec_command('bluetoothctl --timeout '+str(a.scan_seconds)+' scan '+mode+' >/dev/null 2>&1',timeout=a.scan_seconds+10)
 for n in range(a.rounds):
  stage='Wi-Fi SSH connection';data=connect(a.wifi_host)
  timer=threading.Timer(120,data.close);timer.daemon=True;timer.start()
  start=time.monotonic();stage='upload'
  i,o,e=data.exec_command('sha256sum',timeout=45)
  i.write(payload);i.channel.shutdown_write();digest=o.read().decode().split()
  if o.channel.recv_exit_status()!=0 or not digest or digest[0]!=hashlib.sha256(payload).hexdigest():raise RuntimeError('Upload checksum mismatch')
  upload=time.monotonic()-start;start=time.monotonic();stage='download'
  _,o,e=data.exec_command('head -c '+str(size)+' /dev/zero',timeout=45)
  h=hashlib.sha256();count=0
  while block:=o.read(65536):h.update(block);count+=len(block)
  if o.channel.recv_exit_status()!=0 or count!=size or h.hexdigest()!=hashlib.sha256(bytes(size)).hexdigest():raise RuntimeError('Download checksum mismatch')
  row={'round':n+1,'upload_seconds':round(upload,3),'download_seconds':round(time.monotonic()-start,3),'both_checksums_match':True}
  report['rounds'].append(row);print(json.dumps(row),flush=True)
  timer.cancel();timer=None;data.close();data=None
except Exception as error:
 # Exception strings can include addresses; publish only the type and phase.
 report['failure']={'stage':stage,'type':type(error).__name__}
finally:
 if timer:timer.cancel()
 if data:data.close()
 command(control,'bluetoothctl scan off >/dev/null 2>&1 || true')
 if peer:
  result=peer[1].read().decode(errors='replace');rc=peer[1].channel.recv_exit_status()
  errors=peer[2].read().decode(errors='replace')
  summary=re.search(r'(\d+) sent, (\d+) received',result)
  report['paired_peer_echo']={'sent':int(summary[1]) if summary else None,'received':int(summary[2]) if summary else None,'exit_status':rc,'pass':bool(summary and rc==0 and summary[1]==summary[2] and int(summary[1])==60)}
  if errors:
   errors=re.sub(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}','<peer>',errors)
   errors=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<address>',errors)
   report['paired_peer_echo']['diagnostic']=errors.strip()[:200]
 after=command(control,'dmesg');new=after[len(before):] if after.startswith(before) else after
 report['log_contiguous']=after.startswith(before)
 report['taint_after']=command(control,'cat /proc/sys/kernel/tainted').strip()
 signatures=['Timeout cmd id','host_to_card failed','write CFG reg failed','unknown upload type','invalid packet,','card_to_host_mpa failed','card 0001 removed','no free cmd node','Opcode']
 report['kernel_failure_counts']={key:sum(key in line for line in new.splitlines()) for key in signatures}
 report['pass']=len(report['rounds'])==a.rounds and report['taint_after']=='0' and report['log_contiguous'] and not any(report['kernel_failure_counts'].values()) and (not peer or report['paired_peer_echo']['pass'])
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));control.close()
raise SystemExit(0 if report['pass'] else 1)
