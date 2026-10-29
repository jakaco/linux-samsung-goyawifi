#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the real boot-deploy CLI and independently read its FDT handoff."""
from pathlib import Path
import gzip,hashlib,struct,subprocess,sys,tempfile,unittest
PACKER=Path(__file__).with_name('goyawifi-mkbootimg')
if not PACKER.exists():PACKER=Path(__file__).with_name('goyawifi-mkbootimg.py')
class Layout(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
  k=bytearray(4096);struct.pack_into('<III',k,36,0x016f2818,0,4096);self.kernel=bytes(k)
  self.rd=gzip.compress(b'distribution initramfs fixture',mtime=0)
  (self.p/'ramdisk').write_bytes(self.rd)
  self.dtb('samsung,goyawifi')
 def tearDown(self):self.tmp.cleanup()
 def dtb(self,compatible):
  dts=f'/dts-v1/; / {{ compatible="{compatible}"; #address-cells=<1>; #size-cells=<1>; memory@0 {{device_type="memory";reg=<0 0x40000000>;}}; }};'
  subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',str(self.p/'dtb')],input=dts.encode(),check=True)
  (self.p/'kernel').write_bytes(self.kernel+(self.p/'dtb').read_bytes())
 def run_packer(self,extra=(),ok=True):
  args=[sys.executable,str(PACKER),'--kernel',str(self.p/'kernel'),'--ramdisk',str(self.p/'ramdisk'),'--base','0x10000000','--second_offset','0x00f00000','--cmdline','keep_bootcon root=UUID=example','--kernel_offset','0x00008000','--ramdisk_offset','0x01000000','--tags_offset','0x00000100','--pagesize','2048','--header_version','0','-o',str(self.p/'boot.img')]+list(extra)
  result=subprocess.run(args,capture_output=True)
  self.assertEqual(result.returncode==0,ok,result.stderr.decode())
 def test_boot_deploy_roundtrip(self):
  self.run_packer();data=(self.p/'boot.img').read_bytes();self.assertEqual(data[:8],b'ANDROID!')
  ks,ka,rs,ra=struct.unpack_from('<IIII',data,8);self.assertEqual(ka,0x10008000)
  payload=data[2048:2048+ks];dt=payload[len(self.kernel):];self.assertEqual(struct.unpack_from('>I',dt,4)[0],len(dt))
  (self.p/'payload.dtb').write_bytes(dt)
  def get(prop):return subprocess.check_output(['fdtget','-t','x',str(self.p/'payload.dtb'),'/chosen',prop]).decode().strip()
  start=int(get('linux,initrd-start'),16);end=int(get('linux,initrd-end'),16)
  self.assertEqual(payload[start-ka:end-ka],self.rd)
  cmd=subprocess.check_output(['fdtget',str(self.p/'payload.dtb'),'/chosen','bootargs']).decode().strip()
  self.assertEqual(cmd,'keep_bootcon root=UUID=example')
  off=2048+((ks+2047)//2048)*2048;dummy=data[off:off+rs];self.assertIn(b'TRAILER!!!',gzip.decompress(dummy))
  digest=hashlib.sha1()
  for blob in [payload,dummy,b'']:digest.update(blob);digest.update(struct.pack('<I',len(blob)))
  self.assertEqual(data[576:596],digest.digest());self.assertLessEqual(len(data),16777216)
 def test_wrong_board_rejected(self):self.dtb('example,wrong');self.run_packer(ok=False)
 def test_oversize_rejected(self):(self.p/'ramdisk').write_bytes(bytes(16777216));self.run_packer(ok=False)
 def test_wrong_header_rejected(self):self.run_packer(['--header_version','2'],ok=False)
if __name__=='__main__':unittest.main()
