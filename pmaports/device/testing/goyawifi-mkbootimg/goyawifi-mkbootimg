#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SM-T110 image packer compatible with boot-deploy's pxa-mkbootimg CLI.

Samsung ignores boot.img cmdline and supplies a fixed low initrd address.
Carry the distro command line and initramfs through standard DT /chosen
properties instead. The initramfs occupies unused tail space inside the
appended FDT's total size, so the ARM decompressor skips it when placing its
workspace. The kernel itself contains no rootfs or forced command line.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,struct,subprocess,tempfile

def empty_cpio():
 name=b'TRAILER!!!\0';fields=[0,0,0,0,1,0,0,0,0,0,0,len(name),0]
 blob=b'070701'+''.join(f'{v:08x}' for v in fields).encode()+name
 return gzip.compress(blob+bytes((-len(blob))%512),mtime=0)

def make_payload(kernel,dtb,ramdisk,cmdline,load):
 assert struct.unpack_from('<I',kernel,36)[0]==0x016f2818,'not an ARM zImage'
 assert dtb[:4]==bytes.fromhex('d00dfeed'),'missing appended DTB'
 assert struct.unpack_from('>I',dtb,4)[0]==len(dtb),'unexpected DTB length'
 assert ramdisk and len(cmdline.encode())<1024,'empty initramfs or oversized ARM command line'
 assert not any(v.startswith('initrd=') for v in cmdline.split()),'use DT initrd properties, not fixed initrd= arguments'
 with tempfile.TemporaryDirectory(prefix='goyawifi-boot-') as tmp:
  path=Path(tmp)/'board.dtb';path.write_bytes(dtb)
  compatible=subprocess.check_output(['fdtget',str(path),'/','compatible']).decode().split()
  assert 'samsung,goyawifi' in compatible,'image packer is only for the SM-T110'
  subprocess.run(['fdtput','-p','-t','s',str(path),'/chosen','bootargs',cmdline],check=True)
  subprocess.run(['fdtput','-p','-t','x',str(path),'/chosen','samsung,goyawifi-initrd-size',f'{len(ramdisk):x}'],check=True)
  for prop in ['linux,initrd-start','linux,initrd-end']:
   subprocess.run(['fdtput','-p','-t','x',str(path),'/chosen',prop,'0'],check=True)
  size=path.stat().st_size;gap=4096;start=load+len(kernel)+size+gap;end=start+len(ramdisk)
  assert end<0x17000000,'payload reaches the reserved framebuffer region'
  for prop,value in [('linux,initrd-start',start),('linux,initrd-end',end)]:
   subprocess.run(['fdtput','-t','x',str(path),'/chosen',prop,f'{value:x}'],check=True)
  dtb=bytearray(path.read_bytes());assert len(dtb)==size
  # Account for the initramfs as trailing FDT free space, not DT structure.
  struct.pack_into('>I',dtb,4,len(dtb)+gap+len(ramdisk))
  combined=bytes(dtb)+bytes(gap)+ramdisk;path.write_bytes(combined)
  assert subprocess.check_output(['fdtget',str(path),'/chosen','bootargs']).decode().strip()==cmdline
 return kernel+combined,{'initrd_start':hex(start),'initrd_end':hex(end),'initrd_bytes':len(ramdisk),'fdt_bytes':len(combined)}

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--kernel',type=Path,required=True)
 ap.add_argument('--dtb',type=Path)
 ap.add_argument('--ramdisk',type=Path,required=True)
 ap.add_argument('--cmdline',default='')
 ap.add_argument('-o','--output',type=Path,required=True)
 for name,default in [('base',0x10000000),('kernel_offset',0x8000),('ramdisk_offset',0x1000000),('second_offset',0xf00000),('tags_offset',0x100),('pagesize',2048),('header_version',0)]:
  ap.add_argument('--'+name,type=lambda x:int(x,0),default=default)
 ap.add_argument('--pad-to-partition',action='store_true')
 a=ap.parse_args();assert a.header_version==0 and a.pagesize==2048
 assert a.base==0x10000000 and a.kernel_offset==0x8000,'unverified load address'
 k=a.kernel.read_bytes()
 if a.dtb:dt=a.dtb.read_bytes()
 else:
  size=struct.unpack_from('<I',k,44)[0]-struct.unpack_from('<I',k,40)[0]
  assert 0<size<len(k),'input must be zImage with one appended DTB'
  k,dt=k[:size],k[size:]
 payload,metadata=make_payload(k,dt,a.ramdisk.read_bytes(),a.cmdline,a.base+a.kernel_offset)
 rd=empty_cpio();h=bytearray(a.pagesize);h[:8]=b'ANDROID!'
 struct.pack_into('<10I',h,8,len(payload),a.base+a.kernel_offset,len(rd),a.base+a.ramdisk_offset,0,a.base+a.second_offset,a.base+a.tags_offset,a.pagesize,0,0)
 h[48:56]=b'goyawifi';cl=a.cmdline.encode();h[64:64+min(len(cl),512)]=cl[:512]
 if len(cl)>512:h[608:608+len(cl)-512]=cl[512:]
 digest=hashlib.sha1()
 for blob in [payload,rd,b'']:digest.update(blob);digest.update(struct.pack('<I',len(blob)))
 h[576:596]=digest.digest()
 pad=lambda blob:blob+bytes((-len(blob))%a.pagesize)
 image=bytes(h)+pad(payload)+pad(rd);assert len(image)<=16777216,'KERNEL partition limit exceeded; use split initramfs'
 if a.pad_to_partition:image+=bytes(16777216-len(image))
 a.output.write_bytes(image)
 metadata.update({'bytes':len(image),'sha256':hashlib.sha256(image).hexdigest(),'cmdline':a.cmdline,'layout':'zImage + FDT with external initramfs in trailing free space'})
 print(json.dumps(metadata,indent=2))
if __name__=='__main__':main()
