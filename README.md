# Linux for Samsung Galaxy Tab 3 Lite SM-T110

Experimental Linux port for **SM-T110 / samsung-goyawifi / Marvell PXA986 A0**. This is a reproducible patch set and distribution overlay against a pinned upstream kernel, rather than a fork containing the entire Linux history. It has booted a pmbootstrap-generated Linux rootfs on real hardware with stock Phosh.

**Only SM-T110 is tested.** T111, T113 and T116 are different targets. This is a development port with local board-specific drivers, not an upstream-supported kernel or a complete ready-to-flash operating system. Read the hardware limits before installing.

## Build

On Linux, install Git, patch, Python **3.12+**, LLVM/Clang and LLD, make, a C compiler, flex, bison, bc, OpenSSL/ELF development headers, zstd, dtc and **pahole 1.26+**. The standalone build was tested with LLVM 18 and pahole 1.32. Check `pahole --version`; older distro packages may be insufficient. Provide `llvm-objcopy`, `llvm-strip` and the other LLVM tools on PATH.

```sh
python3 prepare-source.py
sh build-kernel.sh "$PWD/kernel-work/linux-f909e534f5e34feb2ea2701d54df63e21aa506fc" \
  "$PWD/build-goyawifi" "$PWD/stage-goyawifi"
```

The preparer checks the upstream archive SHA256, applies four patches, and verifies all **73** exported source files against the tested tree. It refuses to overwrite an existing source tree. Use `--archive PATH` to reuse a download or `--output DIRECTORY` for another clean preparation.

The build stages a normal zImage, DTB, config and modules. It does **not** flash a device. The tested base is Linux commit `f909e534f5e34feb2ea2701d54df63e21aa506fc` (7.3-rc7), recorded in `source-manifest.json`. Never mix modules from builds that only happen to share the same release string.

## Hardware status

Working interfaces include two CPU cores, CPU/GPU/DDR frequency scaling, voltage/thermal controls, DRM/KMS and etnaviv GC1000 GLES2, backlight, touch/buttons, eMMC/microSD, battery/charger monitoring, RTC, ALSA speaker/headphones/microphones, accelerometer and V4L2 rear-camera capture. These were developed and tested on one tablet; see [hardware status](docs/HARDWARE.md) for coverage limits.

USB networking uses the normal initramfs configfs gadget. The accompanying generic RNDIS descriptor patch enables the existing Windows signed driver to bind. Private power/USB/radio startup daemons have been retired. Standard desktop services such as BlueZ, NetworkManager, PulseAudio and iio-sensor-proxy are still expected.

**Known blockers:** intermittent shared Wi-Fi/Bluetooth firmware/bus stalls; normal distro suspend not reliable; DDR self-refresh unproven; shared-I2C stall root cause unresolved; GPS and video decoding lack complete generic kernel/media-stack integration. Proprietary firmware and the previous custom userspace decoders are not included. Stock mpv will not automatically gain hardware decoding.

The [radio investigation and reproducible stress test](docs/RADIO.md) records controlled results and rejected candidates. A successful short ping is not treated as a reliability fix.

Phosh/Phoc uses hardware GLES2 composition, but modern GTK4 applications need Cairo rendering because their GL path requires GLES3. Unlock, typing, touch, brightness and screen blank/wake were owner-tested; Phosh remains sluggish. Weston is a lighter alternative. Screen blanking is not evidence of system suspend.

## Distribution integration and recovery

See [postmarketOS integration](docs/POSTMARKETOS.md) for APK recipes, Phosh configuration and the initramfs patch. The pinned pmaports snapshot identifies its rootfs as Nura edge; this is not an official downloadable SM-T110 Phosh release. Latest local recipe revisions are kernel `7.3_rc7-r10`, device `5-r6`, and generic initramfs `3.12.5-r2`.

Samsung's loader needs the supplied board packer/FDT initramfs handoff. A generic Android header-only packer is insufficient. KERNEL is **16 MiB**; split large distribution initramfs contents rather than enlarging the image. Read [boot and recovery](docs/RECOVERY.md) before writing anything. There are no universal private rootfs images, credentials, per-device radio addresses or signing keys here.

## Validation and contributions

The kernel and device APKs were built in an isolated official pmbootstrap workflow. The installed r10 kernel booted; normal APK triggers generated and wrote its boot image, and every generated image byte was read back from KERNEL. Recovery remained unchanged. The separate standalone build passed earlier. Two ARM32 BPF arena `resolve_btfids` warnings remain; BPF arena support is not claimed.

CI checks source preparation and the boot-image layout tests; it does not boot hardware. Local metadata records source/package hashes. Package maintainer fields are intentionally unset until a real maintainer provides their identity. Nothing has been submitted to Linux or postmarketOS upstream. Contributions should include logs with personal identifiers removed, exact build versions and repeatable hardware tests.

Kernel patches retain their original license notices, principally GPL-2.0; see [licensing and sources](NOTICE.md). Board image tooling is MIT. Firmware is separate and its redistribution status is not asserted here.
