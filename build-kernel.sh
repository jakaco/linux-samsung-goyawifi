#!/bin/sh
# Build a patched source tree using the normal Linux build system.
set -eu
src=${1:?Usage: build-kernel.sh PATCHED_SOURCE [BUILD_DIR] [DESTDIR]}
build=${2:-"$PWD/build-goyawifi"}
dest=${3:-"$PWD/stage-goyawifi"}
src=$(realpath "$src")
mkdir -p "$build" "$dest/boot"
build=$(realpath "$build")
dest=$(realpath "$dest")
export KBUILD_BUILD_USER=goyawifi KBUILD_BUILD_HOST=builder
export KBUILD_BUILD_VERSION=1
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1793145600}
export KBUILD_BUILD_TIMESTAMP=${KBUILD_BUILD_TIMESTAMP:-"Wed Oct 28 00:00:00 UTC 2026"}
PAHOLE=${PAHOLE:-pahole}
export PAHOLE
make -C "$src" O="$build" ARCH=arm LLVM=1 PAHOLE="$PAHOLE" goyawifi_defconfig
make -C "$src" O="$build" ARCH=arm LLVM=1 PAHOLE="$PAHOLE" -j"${JOBS:-8}" \
 zImage modules marvell/pxa986-samsung-goyawifi.dtb
make -C "$src" O="$build" ARCH=arm LLVM=1 PAHOLE="$PAHOLE" \
 INSTALL_MOD_PATH="$dest/usr" INSTALL_MOD_STRIP=1 modules_install
install -m644 "$build/arch/arm/boot/zImage" "$dest/boot/vmlinuz"
install -m644 "$build/System.map" "$dest/boot/System.map"
install -m644 "$build/.config" "$dest/boot/config"
mkdir -p "$dest/boot/dtbs/marvell" "$dest/usr/share/kernel/samsung-goyawifi"
install -m644 "$build/arch/arm/boot/dts/marvell/pxa986-samsung-goyawifi.dtb" \
 "$dest/boot/dtbs/marvell/pxa986-samsung-goyawifi.dtb"
install -m644 "$build/include/config/kernel.release" \
 "$dest/usr/share/kernel/samsung-goyawifi/kernel.release"
