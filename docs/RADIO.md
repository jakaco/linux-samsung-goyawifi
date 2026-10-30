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

## Changes through kernel recipe r18

The current patch retains chip-specific corrections rather than a startup repair service:

* Use the legacy 16-byte TxPD in ordinary, null and A-MSDU packets, including WMM next-packet length calculations. The earlier workaround missed the aggregate constructor.
* Do not read modern RxPD flags from SD8777's 16-byte descriptor: that byte belongs to the packet payload on this chip.
* Keep normal Bluetooth firmware auto-sleep enabled; forcing it awake performed worse in the controlled discovery comparison.
* Avoid unsupported WLAN `STA_CONFIGURE` (0x23f), retaining the existing HT20 fallback, and use legacy scanning as in the vendor driver.
* Conservatively disable multi-port SDIO TX/RX batching only for SD8777. The chip ID is checked directly because interface initialization precedes adapter registration. Other cards retain batching.

The host regression test compiles the actual A-MSDU constructor, descriptor structures and inline helpers. It checks both legacy and other-chip firmware bytes and RX payload preservation. The historical constructor fails the legacy layout check. This establishes a real format bug, not that it caused every observed firmware stall. A sampled reconnect run recorded no A-MSDU constructor calls; hardware execution of that specific path has not been established.

### Hardware observations

All results are from one tablet. Firmware remained 14.66.33.p63, normal DDR scaling was restored, and no private radio daemon was installed.

| Candidate | Result |
| --- | --- |
| r11/r14 vendor-style BT interrupt experiment | Firmware timeouts persisted; experiment reverted |
| r13 normal BT auto-sleep | Discovery/bulk test passed, but paired-phone coexistence still caused WLAN/HCI timeouts |
| r15 legacy scan | Paired-phone coexistence still failed |
| r16 complete TxPD handling | 96 MiB discovery traffic passed; third reconnect timed out and corrupt SDIO headers appeared |
| r18 RX flags + single-port transport | 96 MiB with discovery and another 96 MiB without discovery passed Wi-Fi checksums with no new firmware/HCI timeouts during those intervals; three BT power/WLAN reconnect cycles passed |
| r19 radio-host-only PIO diagnostic | Corrected coexistence test failed during its first upload with firmware/HCI timeouts and SDIO busy errors; rejected and r18 restored |

**r18 is not a complete reliability fix.** Its first boot reported an invalid SDIO packet and card resets; the next boot timed out on RSSI (0xa4), then recovered. Early 512-byte echo results were confounded: btmon showed Linux sending signaling-MTU rejects even while l2ping received replies. The corrected test uses 44 payload bytes plus the 4-byte signaling header, fitting the minimum 48-byte signaling MTU. It still triggered real HCI/WLAN timeouts and a card reset during discovery, although all 96 MiB of Wi-Fi traffic eventually passed. The failing sanitized report is in [tests/results](../tests/results). Connection/discovery success is not evidence of working audio profiles or sustained Bluetooth data.

Established-connection comparisons used one pinned access point. Automatic AP selection was restored afterward; those comparisons do not validate roaming or every AP. Multi-port counters stayed zero during r18 traffic, confirming the transport change took effect. Its separate contribution is not isolated from the RX fix, and no throughput improvement is claimed.

The PIO comparison used the same AP and firmware, with eMMC and microSD still on ADMA. The radio platform device's runtime power control was `on` and status `active`. Failure with radio DMA disabled rules out disabling DMA as a sufficient fix; it does not establish the underlying cause. The PIO host-driver change is not included in this patch set. The r18 desktop, brightness, touch and screen blank/wake passed an owner check before that diagnostic.

The existing legacy format work corresponds to the [SD8777 timeout RFC](https://lists.openwall.net/linux-kernel/2025/10/26/357). Vendor comparisons used [Samsung/Marvell's pinned tree](https://github.com/T110-pmOS/linux_kernel_pxa988/tree/fb2f8b6cd86864c0fcac790e97a372b1772003c7/drivers/marvell/sd8787), including WLAN firmware structures/defaults and `mbtc_src/bt/bt_sdiommc.c`. The vendor sources were checked locally. Reapplying the original partial TxPD workaround is not a new fix.

## Focused controller capture (30 October 2026)

The later private diagnostics did not establish a new reliability fix. The public kernel at the time of this capture was r18; subsequent camera-only revisions retain the same radio patch; raw receive-payload logging, a cross-driver register-capture hook, optional non-HT mode and the experimental clock-delay change are not part of this release.

Additional controls reproduced failures with the Bluetooth hardware driver absent, with stock p46 firmware, with non-HT Wi-Fi, and with both CPUs temporarily kept runnable. An explicit zero host clock-delay candidate also failed. These controls reject those changes as sufficient fixes; they do not identify a single root cause. A 13 MHz attempt overlapped recovery and is excluded as an uncontrolled comparison. Live host unbinding once froze the tablet and is not recommended as a recovery procedure.

The final diagnostic first passed 96 MiB of checksummed Wi-Fi traffic with discovery and three Bluetooth power/WLAN reconnect cycles. Those were short observation windows: a later phone sanity echo failed, HCI command 0x0405 timed out at uptime 185.649 s, and WLAN RSSI command 0xa4 timed out at 186.929 s. Recovery removed and reinitialized the shared card.

At 191.547 s, after that recovery, a 256-byte control-port read completed but its received length field was 33001. The diagnostic captured SDHCI registers immediately on detecting the malformed frame. CMD53 had finished; command/data inhibit bits were clear, all four DAT lines and CMD were high, the 26 MHz card clock was enabled and stable, and interrupt status and ADMA error were zero. The last command was a function-1 fixed-address, byte-mode read of 256 bytes. Its R5 response had no error bits. `HOST_CONTROL2=0` and `FIFO_PARAM=0x5` also showed the vendor-style automatic bus clock-gating bits clear. The subsequent ADDBA-response command 0xcf timed out about 10.101 s later, causing another card reset.

This establishes that **this malformed-response failure was observed with a completed transfer and an idle, clocked controller**, rather than DAT0 already stuck busy. It does not establish that the bytes were correct or explain the earlier RSSI/HCI stall. Firmware output, protocol/framing handling and host-side buffer/coherency corruption remain possible. A later command-timeout counter during recovery must not be confused with the initiating failure. The timeout-only hook never fired for this sequence because there was no data timeout.

The [sanitized controller capture](../tests/results/r24-controller-capture.json) records register values and chronology without packet payloads or device addresses. The associated successful bulk interval and failed phone sanity check are also recorded. No sustained phone echo/coexistence success is claimed. Diagnostic kernels and temporary settings are removed for normal use; further work should target the first firmware-command stall and receive-buffer integrity, rather than assume clock gating or Bluetooth alone is responsible.

## Reproduce without publishing private logs

Install Paramiko on the host. Pin the tablet's SSH host key in your own known_hosts file, and provide your own key and network addresses. For example:

```sh
python3 tests/radio-stress.py \
  --usb-host USB_IP --wifi-host WIFI_IP --host-key-name TABLET_ALIAS \
  --known-hosts /path/to/known_hosts --identity /path/to/ssh_key \
  --scan-seconds 60 --output radio-result.json
```

Run an idle comparison with `--scan-seconds 0`; `--scan-transport bredr` and `le` can isolate discovery modes. The default is three rounds of 16 MiB each direction, checked by SHA256. BlueZ discovery and each transfer pair are bounded. A failure returns a nonzero exit status. Do not run this through Wi-Fi as the only control channel.

The report contains timing, checksums, kernel version, taint and counts of failure signatures. It does not include addresses, credentials, neighbour discoveries or raw dmesg. It is an optional development test, not a tablet startup service. It stops discovery when done, including on a handled test failure. Use `--peer MAC` only for your explicitly selected, already-paired device: it adds a short availability check and a bounded 60-echo, 44-byte L2CAP test. Missing echo summaries are failures, not zero-packet successes. The peer address is not written to the report. It does not prove Bluetooth profiles, suspend, all access points or long-duration stability.
