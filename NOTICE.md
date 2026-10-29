# Licenses and sources

This repository contains patches to the Linux kernel and separate distribution/image integration. Original copyright and SPDX notices are retained. Kernel changes follow their source-file licenses, principally GPL-2.0-only/GPL-2.0-or-later. `COPYING` and the relevant texts under `LICENSES/` are copied from the pinned Linux source; they do not relicense upstream material.

The board image packer, its layout tests and the source preparer carry MIT SPDX identifiers. The device/APK recipes retain their declared licenses. Any firmware fetched by a recipe has its own licensing; firmware binaries are excluded and no redistribution grant for them is asserted here.

Primary source references:

- Linux: https://github.com/torvalds/linux/tree/f909e534f5e34feb2ea2701d54df63e21aa506fc
- pmaports integration baseline: https://gitlab.postmarketos.org/postmarketOS/pmaports/-/tree/1eb4dce28ef2d0ecc8651914bcb4972083eefb0f
- pmbootstrap baseline: https://gitlab.postmarketos.org/postmarketOS/pmbootstrap/-/tree/46ee403e4680002ce42dc2645adf9b08557270e9
- SD8777 firmware recipe upstream: https://github.com/T110-pmOS/marvell_firmware_sd8777

The port incorporates board information and register sequences from the Samsung/Marvell vendor kernel, including the Samsung sensor register table whose original copyright notice is retained. It is a local development port; no affiliation with Samsung, Marvell, Linux maintainers or postmarketOS is implied.

The README and hardware status distinguish hardware tests from unvalidated functionality. Private runtime logs and original device backups are excluded from publication. Do not add another user's network credentials, address files, keys or recovery images to contributions.
