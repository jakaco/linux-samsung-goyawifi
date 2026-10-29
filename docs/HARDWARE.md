# Hardware status

These are development results on one SM-T110. Earlier Alpine-specific tests and the current Phosh rootfs are distinguished below. Normal Linux interfaces do not imply upstream driver review or support on another model.

| Component | Interface and result | Limit |
| --- | --- | --- |
| CPU | Two cores, per-core timers, cpufreq/voltage/thermal controls | Deep sleep coverage is incomplete |
| DDR | Devfreq up to 533 MHz under load | Self-refresh not proven; deeper experiments parked |
| GPU | DRM render node, etnaviv, GC1000 GLES2, devfreq | No GLES3; GTK4 uses Cairo; Xorg glitches unresolved |
| Display | DRM/KMS, Linux LCD/DSI initialization, VX5B3D cold initialization | Board-specific driver and shared-I2C workaround remain |
| Backlight | Standard backlight class linked to DRM blanking | Blank/unblank is not full system suspend |
| Touch/buttons | Standard input events; aligned Phosh touch and Power blank/wake owner-tested | Full suspend wake depends on incomplete system PM |
| eMMC/microSD | MMC/block interfaces; prior card detection, I/O and safe-eject tests | Avoid modifying the outer Samsung partition layout |
| Battery/charging | power_supply, charger controls, UPower | Charge percentage is an estimate, not calibrated coulomb counting |
| RTC | RTC/alarm support, earlier wake tests | Standard distro suspend currently blocked elsewhere |
| Sound | ALSA/UCM, speaker, headphones, built-in/headset microphones; earlier full duplex tests | Current generic PulseAudio playback/capture passed; headset/full-duplex server path needs revalidation |
| Accelerometer | IIO, iio-sensor-proxy; tilt/orientation tested | Native landscape is currently locked in Phosh |
| Wi-Fi | mwifiex SD8777, NetworkManager, association and downloads tested | Intermittent CMD53/firmware stalls; not production reliable |
| Bluetooth | btmrvl/BlueZ; automatic HCI discovery and per-device address setup | Earlier pairing/OBEX worked; current coexistence and host sleep remain unreliable |
| Camera | Standard V4L2 rear-camera capture | Stock camera GUI and performance require further testing |
| GPS | Earlier proprietary userspace could receive satellites | No complete generic GNSS implementation or reliable-fix claim |
| Video decoding | Earlier proprietary engine/custom adapter played multiple codecs | No generic V4L2 stateless decoder integration in this release |
| System suspend | Earlier Alpine CPU-cluster wake succeeded | Normal elogind suspend failed in SD8777 host sleep; automatic suspend disabled |
| Recovery reboot | Kernel restart-prepare flag code included | restart2 recovery tests returned to Linux; recovery selection not validated |

The shared I2C recovery work has reduced observed faults but has not established the electrical/controller cause. A clean boot can report zero timeouts and still does not prove the issue solved. Likewise, no measured suspend power consumption is available.

Current Phosh uses the GC1000 for composition, with scale 1 and native 1024x600 landscape. Lock-screen keypad, keyboard typing, brightness and screen blank/wake passed owner checks after r10. Interaction is sluggish despite available RAM. This is a usability limitation, not evidence that Phoc fell back to llvmpipe.

Hardware performance watchpoints/breakpoints are skipped on PXA986 A0 because probing its debug registers traps. Two ARM32 BPF arena symbol-resolution warnings remain in the build; BPF arena functionality is not claimed.
