# SD8777 reliability investigation

The shared Wi-Fi/Bluetooth problem is reproducible. A connected NetworkManager state and successful short pings do not establish reliability. Use USB as the control path while stressing Wi-Fi and BlueZ discovery.

## Controlled results on the r10 baseline

Both firmware versions used the same kernel, calibration, pinned access point and conservative power policy for the established-connection tests. Firmware overrides were temporary and did not replace the installed firmware. No firmware binaries or device addresses are published here.

| Firmware | Bluetooth activity | Checksummed traffic | Result |
| --- | --- | --- | --- |
| 14.66.33.p46 | Powered, idle | 48 MiB upload + 48 MiB download | Passed |
| 14.66.33.p63 | Powered, idle | 48 MiB upload + 48 MiB download | Passed |
| 14.66.33.p46 | 60 seconds of discovery | 48 MiB upload + 48 MiB download | Passed; much slower during discovery |
| 14.66.33.p63 | 60 seconds of discovery | First transfer interrupted | Bluetooth inquiry cancellation and WLAN RSSI command timed out; card reset |

An earlier p46 reconnect/discovery attempt also failed; that test overlapped IP configuration and is not directly comparable. Therefore these results do not establish p46 as a complete fix. Firmware downgrade alone is not the published solution.

The boot log also captured an unrecognised upload type followed by repeated block-ack requests, command-node exhaustion and a timeout. The SDHCI error counters remained zero in the sampled failures. This narrows the investigation but does not by itself prove an RF, firmware or protocol root cause.

An SD8777-only candidate matching the vendor Bluetooth byte-status/ack interrupt path was tested in kernel recipe r11. It did not fix the problem and is being reverted; it is not part of the published stable patch set. That trace caught a timeout on `STA_CONFIGURE` (0x23f), a channel query which this firmware normally rejects with result 2. The next candidate avoids issuing that unsupported query and retains the existing HT20 fallback. It is not declared validated until its hardware tests pass.

The existing port already has a chip-scoped legacy TxPD/alignment workaround corresponding to the [SD8777 timeout RFC](https://lists.openwall.net/linux-kernel/2025/10/26/357). Applying that workaround again is not a new fix. The vendor interrupt comparison used [Samsung/Marvell bt_sdiommc.c](https://github.com/T110-pmOS/linux_kernel_pxa988/blob/fb2f8b6cd86864c0fcac790e97a372b1772003c7/drivers/marvell/sd8787/mbtc_src/bt/bt_sdiommc.c); the exact fetched source was checked locally before the experiment.

## Reproduce without publishing private logs

Install Paramiko on the host. Pin the tablet's SSH host key in your own known_hosts file, and provide your own key and network addresses. For example:

```sh
python3 tests/radio-stress.py \
  --usb-host USB_IP --wifi-host WIFI_IP --host-key-name TABLET_ALIAS \
  --known-hosts /path/to/known_hosts --identity /path/to/ssh_key \
  --scan-seconds 60 --output radio-result.json
```

Run an idle comparison with `--scan-seconds 0`; `--scan-transport bredr` and `le` can isolate discovery modes. The default is three rounds of 16 MiB each direction, checked by SHA256. BlueZ discovery and each transfer pair are bounded. A failure returns a nonzero exit status. Do not run this through Wi-Fi as the only control channel.

The report contains timing, checksums, kernel version, taint and counts of failure signatures. It does not include addresses, credentials, neighbour discoveries or raw dmesg. It is an optional development test, not a tablet startup service. It stops discovery when done, including on a handled test failure. It does not prove paired-device transfers, audio profiles, suspend, all access points or long-duration stability.
