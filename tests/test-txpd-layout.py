#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the real kernel A-MSDU constructor and verify its firmware bytes."""
from pathlib import Path
import argparse,re,subprocess,tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',required=True,type=Path,help='Prepared Linux source tree')
p.add_argument('--aggregation-source',type=Path,help='Optional historical 11n_aggr.c for demonstrating the regression')
a=p.parse_args();driver=a.source/'drivers/net/wireless/marvell/mwifiex'
fw=(driver/'fw.h').read_text();main=(driver/'main.h').read_text()
aggr=(a.aggregation_source or driver/'11n_aggr.c').read_text()
wire=re.search(r'struct txpd \{.*?\} __packed;',fw,re.S).group()
rx_wire=re.search(r'struct rxpd \{.*?\} __packed;',fw,re.S).group()

def function(text,name,prefix):
 location=text.index(name+'(');start=text.rfind(prefix,0,location)
 assert start>=0
 opening=text.index('{',location);depth=1;end=opening+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]

helper=function(main,'mwifiex_txpd_len','static inline u16')
rx_helper=function(main,'mwifiex_rxpd_flags','static inline u8')
constructor=function(aggr,'mwifiex_11n_form_amsdu_txpd','static void')
defines=[]
headers=fw+'\n'+(driver/'11n_aggr.h').read_text()
for name in ['PKT_TYPE_AMSDU','MWIFIEX_TXPD_FLAGS_TDLS_PACKET','MWIFIEX_TxPD_POWER_MGMT_LAST_PACKET']:
 defines.append(re.search(r'^#define\s+'+name+r'\s+[^\n]+',headers,re.M).group())
program=r'''
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <endian.h>
typedef uint8_t u8; typedef int8_t s8; typedef uint16_t u16; typedef uint32_t u32;
typedef u16 __le16; typedef u32 __le32;
#define __packed __attribute__((packed))
#define BIT(n) (1U << (n))
#define cpu_to_le16(v) htole16(v)
#define cpu_to_le32(v) htole32(v)
#define MWIFIEX_BUF_FLAG_TDLS_PKT BIT(0)
#define MWIFIEX_BSS_ROLE_STA 0
#define GET_BSS_ROLE(priv) 0
'''+'\n'.join(defines)+'\n'+wire+'\n'+rx_wire+r'''
struct mwifiex_adapter { bool sd8777_legacy_txpd, pps_uapsd_mode, tx_lock_flag; };
struct mwifiex_private { struct mwifiex_adapter *adapter; u32 pkt_tx_ctrl; u8 bss_num,bss_type; };
struct mwifiex_txinfo { u32 flags; };
struct sk_buff { u8 *data; unsigned int len,priority; struct mwifiex_txinfo cb; };
#define MWIFIEX_SKB_TXCB(skb) (&(skb)->cb)
static void *skb_push(struct sk_buff *skb,unsigned int n) { skb->data-=n;skb->len+=n;return skb->data; }
static u8 mwifiex_wmm_compute_drv_pkt_delay(struct mwifiex_private *p,struct sk_buff *s) { (void)p;(void)s;return 7; }
static bool mwifiex_check_last_packet_indication(struct mwifiex_private *p) { (void)p;return false; }
'''+helper+'\n'+rx_helper+'\n'+constructor+r'''
static int check(bool legacy) {
 u8 storage[128],payload[32],expected[20]={0};
 unsigned int length=legacy?16:20;
 struct mwifiex_adapter adapter={.sd8777_legacy_txpd=legacy};
 struct mwifiex_private priv={.adapter=&adapter,.pkt_tx_ctrl=0x11223344,.bss_num=7,.bss_type=1};
 struct sk_buff skb={.data=storage+64,.len=sizeof(payload),.priority=5};
 memset(storage,0xcc,sizeof(storage));
 for(unsigned int i=0;i<sizeof(payload);i++)payload[i]=(u8)(0xa0+i);
 memcpy(skb.data,payload,sizeof(payload));
 mwifiex_11n_form_amsdu_txpd(&priv,&skb);
 if(skb.len!=sizeof(payload)+length) {
  fprintf(stderr,"%s descriptor length mismatch: got %u, expected %zu\n",legacy?"legacy":"modern",skb.len,sizeof(payload)+length);return 10;
 }
 expected[0]=1;expected[1]=7;expected[2]=sizeof(payload);expected[4]=length;
 expected[6]=PKT_TYPE_AMSDU&0xff;expected[7]=PKT_TYPE_AMSDU>>8;
 expected[8]=0x44;expected[9]=0x33;expected[10]=0x22;expected[11]=0x11;
 expected[12]=5;expected[14]=7;
 if(memcmp(skb.data,expected,length) || memcmp(skb.data+length,payload,sizeof(payload))) {
  fprintf(stderr,"%s descriptor/payload firmware bytes differ\n",legacy?"legacy":"modern");return 11;
 }
 printf("PASS: %s A-MSDU descriptor %u bytes, exact firmware fields, payload preserved\n",legacy?"SD8777":"other-chip",length);
 return 0;
}
static int check_rx(bool legacy) {
 u8 storage[64],original[64];struct rxpd *pd=(void *)storage;
 struct mwifiex_adapter adapter={.sd8777_legacy_txpd=legacy};
 memset(storage,0x5a,sizeof(storage));pd->flags=0xa5;
 pd->rx_pkt_offset=cpu_to_le16(legacy?16:sizeof(*pd));
 memcpy(original,storage,sizeof(storage));
 if(mwifiex_rxpd_flags(&adapter,pd)!=(legacy?0:0xa5) || memcmp(storage,original,sizeof(storage))) {
  fprintf(stderr,"RX flags interpreted payload or modified packet bytes\n");return 12;
 }
 printf("PASS: %s RX flags contract, packet bytes unchanged\n",legacy?"SD8777":"other-chip");return 0;
}
int main(void) {
 int ret=check(false);if(ret)return ret;ret=check(true);if(ret)return ret;
 ret=check_rx(false);return ret?ret:check_rx(true);
}
'''
with tempfile.TemporaryDirectory(prefix='mwifiex-txpd-test-') as tmp:
 source=Path(tmp)/'test.c';binary=Path(tmp)/'test';source.write_text(program)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True)
 raise SystemExit(subprocess.call([str(binary)]))
