#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the driver's real configure/start functions against lifecycle stubs."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', required=True, type=Path)
a = p.parse_args()
text = (a.source / 'drivers/media/platform/marvell/mcam-core.c').read_text()

def function(name):
    start = text.index('static int ' + name + '(')
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

stub = r'''
#include <assert.h>
#include <stdio.h>
#define ENOMEM 12
#define B_vmalloc 0
#define B_DMA_contig 1
#define B_DMA_sg 2
#define S_STREAMING 2
#define CF_DMA_ACTIVE 0
#define CF_SG_RESTART 1
#define V4L2_MBUS_CSI2_DPHY 4
#define spin_lock_irqsave(lock, flags) ((void)(lock), (flags)=0)
#define spin_unlock_irqrestore(lock, flags) ((void)(lock), (void)(flags))
struct mcam_camera {
 int dev_lock, buffer_mode, nbufs, bus_type, state, config_needed, t110_csi;
 unsigned long flags;
 int allocations_fail, sensor_configs, image_configs, dma_setups, starts;
 int sensor_starts, sensor_error, stops;
 int owned[2];
 void (*dma_setup)(struct mcam_camera *);
};
static void clear_bit(int bit, unsigned long *flags) { *flags &= ~(1UL << bit); }
static int test_bit(int bit, unsigned long *flags) { return !!(*flags & (1UL << bit)); }
static int mcam_alloc_dma_bufs(struct mcam_camera *cam, int ignored) { return cam->allocations_fail; }
static int mcam_needs_config(struct mcam_camera *cam) { return cam->config_needed; }
static void mcam_set_config_needed(struct mcam_camera *cam, int needed) { cam->config_needed=needed; }
static void mcam_cam_configure(struct mcam_camera *cam) { cam->sensor_configs++; }
static void mcam_ctlr_image(struct mcam_camera *cam) { cam->image_configs++; }
static void mcam_reset_buffers(struct mcam_camera *cam) { (void)cam; }
static void mcam_enable_mipi(struct mcam_camera *cam) { (void)cam; }
static void mcam_disable_mipi(struct mcam_camera *cam) { (void)cam; }
static void mcam_ctlr_irq_enable(struct mcam_camera *cam) { (void)cam; }
static void mcam_ctlr_stop_dma(struct mcam_camera *cam) { cam->state=0; cam->stops++; }
static int sensor_stream(struct mcam_camera *cam, int on) {
 assert(on && cam->owned[0] && cam->owned[1] && cam->starts);
 cam->sensor_starts++;
 return cam->sensor_error;
}
#define sensor_call(cam, group, op, value) sensor_stream(cam, value)
static void dma_setup(struct mcam_camera *cam) {
 assert(!cam->owned[0] && !cam->owned[1]);
 cam->owned[0]=1; cam->owned[1]=1; cam->dma_setups++;
}
static void mcam_ctlr_start(struct mcam_camera *cam) {
 assert(cam->owned[0] && cam->owned[1]);
 cam->starts++;
}
'''
main = r'''
int main(void) {
 for (int mode=B_DMA_contig; mode<=B_DMA_sg; mode++) {
  struct mcam_camera cam = {.buffer_mode=mode, .config_needed=1, .dma_setup=dma_setup, .t110_csi=(mode==B_DMA_contig)};
  assert(mcam_read_setup(&cam)==0);
  assert(cam.dma_setups==1 && cam.sensor_configs==1 && cam.image_configs==1);
  /* Model STREAMOFF returning the hardware-owned buffers. No S_FMT follows. */
  cam.owned[0]=0; cam.owned[1]=0; cam.state=0;
  cam.flags=(1UL << CF_DMA_ACTIVE);
  assert(mcam_read_setup(&cam)==0);
  assert(cam.dma_setups==2 && cam.starts==2 && cam.state==S_STREAMING);
  assert(cam.sensor_configs==1 && cam.image_configs==1);
  assert(!test_bit(CF_DMA_ACTIVE,&cam.flags) && !test_bit(CF_SG_RESTART,&cam.flags));
  cam.owned[0]=0; cam.owned[1]=0; cam.state=0;
  cam.flags=(1UL << CF_DMA_ACTIVE) | (1UL << CF_SG_RESTART);
  assert(mcam_read_setup(&cam)==0);
  assert(cam.dma_setups==3 && cam.starts==3);
  assert(cam.sensor_starts==(cam.t110_csi ? 3 : 0));
 }
 struct mcam_camera fail = {.buffer_mode=B_vmalloc, .allocations_fail=1, .dma_setup=dma_setup};
 assert(mcam_read_setup(&fail)==-ENOMEM && fail.dma_setups==0 && fail.starts==0);
 struct mcam_camera sensor_fail = {.buffer_mode=B_DMA_contig, .t110_csi=1, .config_needed=1, .dma_setup=dma_setup, .sensor_error=-5};
 assert(mcam_read_setup(&sensor_fail)==-5 && sensor_fail.stops==1 && sensor_fail.state==0);
 puts("PASS: retained-format DMA restart in contiguous/SG modes; allocation failure before start");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='mcam-restart-') as temp:
    source = Path(temp) / 'test.c'
    binary = Path(temp) / 'test'
    source.write_text(stub + function('mcam_ctlr_configure') + '\n' + function('mcam_read_setup') + main)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Wno-unused-parameter', str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
