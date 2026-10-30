# Boot, recovery and installation boundaries

Only SM-T110 / PXA986 A0 is tested. Confirm the model from the device/recovery, not a similarly named tablet listing. Preserve a working recovery and a complete backup of the original partition layout, boot partition and user data before replacing an installation. Rootfs images can erase user data; this repository deliberately does not run a flasher.

Samsung's loader ignores the Android header command line and supplies an obsolete low initrd address. The supplied `goyawifi-mkbootimg.py` accepts the boot-deploy PXA interface, records the command line in DT `/chosen`, and carries the external distribution initramfs in reserved FDT tail space. A board fixup derives its address after relocation and updates the early FDT checksum/reservation. This board-specific handoff is still required.

Image parameters are Android header v0, page size 2048, base 0x10000000, kernel offset 0x8000, ramdisk offset 0x01000000 and tags offset 0x100. **KERNEL is 16 MiB**. Do not truncate an oversized image or change partition sizes to make it fit. The distro overlay uses split initramfs with gzip for initramfs-extra. The Android header ramdisk field holds an empty placeholder archive.

The tested installation preserves the outer Samsung layout, bootloader, EFS and recovery. Its combined distribution GPT image is inside USER, with loop-mapped pmOS_boot and pmOS_root. The normal generated boot image contains filesystem UUIDs for its matching rootfs. **Do not flash a boot image built for another rootfs's UUIDs.** Never write a partition image to the whole eMMC device.

Keep the kernel, DTB and modules as a matching build. A successful compile or structural image test does not establish that a freshly generated rootfs boots. The r18 packages were tested through normal upgrades on the installed system, not by distributing a universal flashable image.

No hardware UART was available during development. A working TWRP recovery can retrieve persistent last-kmsg logs after some failed boots. The tested physical recovery sequence is Volume Up + Home + Power. Keep USB connected and collect logs before another reboot when possible. Do not depend on software recovery reboot selection: its new restart-prepare code is included, but the current restart2 tests returned to Linux.

Recovery, bootloader and per-device calibration are intentionally not distributed. Restore only your own verified backups to the matching partitions. The source bundle contains no Wi-Fi credentials, device addresses, SSH host/private keys, APK signing keys or private disk images.
