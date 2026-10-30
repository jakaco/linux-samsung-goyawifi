# Rear camera and standard applications

The fitted rear sensor is SR200PC20M, exposed through the normal V4L2 capture device and Marvell CCIC driver. It advertises UYVY at 640x480, 800x600 and 1600x1200. Exposure affects actual frame rate; the advertised 15 fps is not a guarantee in a dim scene. The old custom camera panel is not required or included.

## Stream lifetime fix in kernel recipe r26

The first Guvcview trial on r18 triggered an interrupt-context NULL-pointer panic in `mcam_dma_contig_done`. STREAMOFF had returned the hardware-owned buffers, but another STREAMON could skip DMA setup when image configuration was retained. The older custom panel's format-setting behavior masked this path.

DMA-buffer setup now runs on every stream start, independently of cached image configuration. For this board's CSI path, stream stop also stops the sensor and disables the CSI receiver, and start invokes the sensor's stream-on operation after preparing the controller. A failed sensor start stops controller DMA and propagates the error. The initial DMA-only candidate avoided the panic but timed out on the second stream; it is not the published solution.

Validation includes:

* The actual driver functions compile and run in [the host lifecycle regression](../tests/test-camera-restart.py). The r18 functions fail the retained-format restart case. This test checks control flow and ownership initialization, not electrical camera behavior.
* On r26, one open V4L2 fd completed three MMAP start/stop cycles without any S_FMT call. Each cycle delivered six complete, distinct VGA frames. [Sanitized result](../tests/results/r26-camera-stream-restart.json).
* Bounded GStreamer capture through `v4l2src`, and through an explicitly targeted PipeWire camera node, each reached EOS after six VGA frames.

To repeat the hardware restart check as your logged-in user with camera access:

```sh
python3 tests/camera-stream-restart.py --device /dev/video0
```

It saves no images. Close other applications actively using the camera first. Host tests and short streaming tests do not establish all GUI operations, all memory modes, suspend or long-duration stability.

## GNOME Snapshot on the tested Phosh installation

Install the ordinary distribution packages: `snapshot`, `pipewire`, `wireplumber`, `gst-plugin-pipewire`, `gst-plugins-rs-gtk4`, `gst-plugins-base`, `gst-plugins-good`, `gst-plugins-bad`, `xdg-desktop-portal`, a suitable desktop portal backend and `xdg-user-dirs`. Run `xdg-user-dirs-update` as the desktop user so Pictures/Videos have normal destinations. The tested session already starts PipeWire/WirePlumber through the distro's normal desktop integration; no board-specific camera service is used.

The V4L2 monitor exposes `marvell_ccic`. Libcamera is not required for this tested capture path. Follow the [WirePlumber camera configuration](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/video.html) and [Snapshot requirements](https://github.com/GNOME/snapshot/tree/51.0).

Snapshot 51.0 reached live preview with this compatibility launch on the tested GTK 4.24.1/PipeWire 1.6.9 stack:

```sh
GDK_DISABLE=gl GSK_RENDERER=cairo GST_PLUGIN_FEATURE_RANK=pipewiresrc:0 snapshot
```

The GC1000's GLES2 does not satisfy GTK4's GL renderer requirements. These GTK settings select its software path; they do not disable the compositor's GLES2 renderer. GTK documents these environment settings as debugging controls, so treat this as a version-specific compatibility workaround, not a stable application API.

An unbound `pipewiresrc` stalled during automatic startup in the local comparison, while an explicitly targeted node delivered frames. Lowering its factory rank avoids the temporary automatic-source path; the app's selected-device PipeWire source can still be instantiated explicitly. The normal portal permission must be accepted by the user. This does not bypass camera permissions.

The owner confirmed live Snapshot preview but reported severe lag. The active format was 800x600 and software rendering consumed substantial CPU; repeated PipeWire buffer-recycling errors were also observed. A satisfactory performance claim, photo saving and video recording are not established by that preview result. The `Unknown factory: jifmux` encoding-profile log alone does not mean that the JPEG plugin is missing: the plugin was present and enumerable as the desktop user.

Guvcview has separate control and preview windows, which fit Phosh poorly. Its initial panic led to the kernel fix, but its UI is not the recommended tablet workflow. Further application results belong here with exact versions and owner checks; do not substitute a decoder or renderer label for visible working capture.
