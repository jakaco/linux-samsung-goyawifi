# Distribution integration

The overlay was built against pmaports `1eb4dce28ef2d0ecc8651914bcb4972083eefb0f` and pmbootstrap `46ee403e4680002ce42dc2645adf9b08557270e9` (3.12.1). The pinned pmaports snapshot identifies its rootfs as Nura edge. Treat rebasing to a different distribution snapshot as a separate compatibility task.

1. Use a separate pmaports checkout at the pinned commit. Move archived goyawifi recipes aside so package names are unique, then copy the directories under this repository's `pmaports/device/testing/` into it.
2. Apply `distro-patches/0001-initramfs-rndis-windows-descriptors.patch` at the pmaports root. Set `main/postmarketos-initramfs` pkgrel to 2 and refresh its source checksums. This is required by device r6 and enables standard configfs RNDIS binding to Windows' existing signed driver. The patch changes only the RNDIS branch.
3. Initialize pmbootstrap against that checkout and select `samsung-goyawifi`, armv7 and a Wayland UI. Replace empty package maintainer fields with your own identity before submitting packages upstream; they are intentionally not attributed to an invented maintainer.
4. Build the kernel, packer, device and patched initramfs explicitly:

```sh
pmbootstrap build --arch armv7 postmarketos-initramfs linux-samsung-goyawifi \
  goyawifi-mkbootimg device-samsung-goyawifi
```

The optional `firmware-samsung-goyawifi` recipe downloads the pinned SD8777 archive used by the archived port. Firmware binaries are not in this repository, and its redistribution status has not been independently resolved. Board calibration and device addresses must come from the target tablet itself.

The device package supplies ALSA UCM, the Mesa KMSRO alias, early etnaviv policy and conservative SDIO runtime-PM udev rules. A normal initramfs, kernel, DTB and matching modules replace the earlier embedded rescue rootfs. Kernel installation uses the normal postmarketos-mkinitfs/boot-deploy APK triggers. The image packer handles this bootloader's FDT/initramfs relocation quirk.

## Stock Phosh configuration used on the tablet

Install the standard Phosh/Phoc packages and the Stevia on-screen keyboard **with `stevia-schemas`** (the missing schema caused a failed login session). The installed setup also has PulseAudio, BlueZ, NetworkManager, iio-sensor-proxy, polkit and brightnessctl. Select `/usr/share/wayland-sessions/phosh.desktop` through normal tinydm.

`/etc/phosh/phoc.ini`:

```ini
[core]
xwayland=true
[output:DSI-1]
rotate=0
scale=1
```

For the tinydm Wayland session environment:

```sh
export WLR_RENDERER=gles2
export GSK_RENDERER=cairo
```

Enable the standard screen keyboard and lock orientation through the desktop settings. The GC1000 supports GLES2 composition, but modern GTK4's GL renderer requires GLES3. Scale 1/native landscape avoids an inaccessible clipped lock-screen keypad. Phosh remains slower than Weston on this hardware.

Keep unattended system sleep disabled until radio host sleep is reliable. Phosh handles screen blanking; do not confuse that with a successful `loginctl suspend`. No private power daemon, radio startup hook, USB setup service, USB signaller or ttyGS0 getty is needed in the tested configuration. The normal RNDIS interface is used for USB networking; configure authentication and networking through ordinary distro tools.

For SD8777, the tested conservative module policy is `options mwifiex cal_data_cfg=mrvl/cal_data.conf disable_auto_ds=1`; NetworkManager powersave is 2 and the device's packaged udev rules hold runtime power on. This does not resolve all observed radio stalls. If configuring Bluetooth's factory address, a private per-device modprobe file may use `options btmrvl bdaddr=XX:XX:XX:XX:XX:XX`; substitute only the target tablet's real address. Never commit it or copy it to all devices.

Audio hardware uses 44.1 kHz S16 stereo, with UCM and a resampling sound server. The generic PulseAudio playback/capture path was exercised. The earlier custom GPS and hardware-video adapters are not provided by these standard desktop packages.

A fresh image generated from this public overlay has not received the same flash/boot validation as the upgraded installed rootfs. There is no ready-to-flash image or universal login password in this repository. Set up your own local account, SSH keys and network credentials.
