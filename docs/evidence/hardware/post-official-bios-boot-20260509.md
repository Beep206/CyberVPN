# Post Official BIOS Flash Boot Evidence

Date: 2026-05-09

Server: `cybervpn-h-ops`, `10.10.10.34`

Flash status:

```text
Official JGINYUE full-chip image was written and verified before reboot.
Server was powered off, power-cycled, and booted successfully.
```

Post-boot firmware identity:

```text
Hardware Vendor: JGINYUE
Hardware Model: X99-D8 Server
BIOS Vendor: American Megatrends Inc.
BIOS Version: 5.11
BIOS Release Date: 05/14/2021
Baseboard: JGINYUE X99-D8 Server V1.0
```

Post-boot service status:

```text
ssh:      active
caddy:    active
fail2ban: active
docker:   active
ufw:      active
```

Network:

```text
enp9s0: 10.10.10.34/24
ens4: down
gateway: 10.10.10.1
ping from control machine: 3/3, 0% loss
```

Memory:

```text
Linux visible memory: 46 GiB
Swap: 31 GiB
NUMA node0: 15926 MB
NUMA node1: 32194 MB
Detected populated DIMMs: 6 x 8 GB
```

Populated DIMMs:

```text
DIMM_C1 8 GB Samsung M393A1G40EB2-CTD
DIMM_D1 8 GB Samsung M393A1G40EB2-CTD
DIMM_E1 8 GB Samsung M393A1G40EB2-CTD
DIMM_F1 8 GB Samsung M393A1G40EB2-CTD
DIMM_G1 8 GB Samsung M393A1G40EB2-CTD
DIMM_H1 8 GB Samsung M393A1G40EB2-CTD
```

Storage health:

```text
HDD /dev/sda SMART overall-health: PASSED
HDD reallocated sectors: 0
HDD pending sectors: 0
HDD offline uncorrectable: 0
HDD temperature: 36 C

NVMe critical_warning: 0
NVMe percentage_used: 0%
NVMe media_errors: 0
NVMe temperature: 38 C
```

Docker:

```text
Docker version: 29.4.3
Docker root: /srv/docker
Storage driver: overlayfs
Live restore: true
CPU visible to Docker: 72
Memory visible to Docker: 50458689536 bytes
```

Caddy local edge health:

```text
https://gitlab.h.cyber-vpn.net/.well-known/cybervpn-edge-health
HTTP 200
ok
```

Evidence files on server:

```text
/srv/cybervpn-h/evidence/hardware/post-official-bios-boot-20260509T182822Z.txt
/srv/cybervpn-h/evidence/hardware/post-official-bios-storage-network-20260509T182841Z.txt
```

Conclusion:

```text
The official BIOS flash did not change the RAM detection issue.
The platform still reports 6 populated DIMMs and an imbalanced 16 GB / 32 GB NUMA memory layout.
This now points to physical DIMM placement, DIMM seating, slot/channel, socket contact, or board-level behavior rather than the previously installed firmware image.
```

Follow-up RAM reseat result:

```text
UTC: 20260509T183701Z
Linux visible memory: 62 GiB
Detected populated DIMMs: 8 x 8 GB
NUMA node0: 32011 MB
NUMA node1: 32237 MB
```

Detected DIMMs after successful reseat:

```text
DIMM_A1 8 GB Samsung M393A1G40EB2-CTD
DIMM_B1 8 GB Samsung M393A1G40EB2-CTD
DIMM_C1 8 GB Samsung M393A1G40EB2-CTD
DIMM_D1 8 GB Samsung M393A1G40EB2-CTD
DIMM_E1 8 GB Samsung M393A1G40EB2-CTD
DIMM_F1 8 GB Samsung M393A1G40EB2-CTD
DIMM_G1 8 GB Samsung M393A1G40EB2-CTD
DIMM_H1 8 GB Samsung M393A1G40EB2-CTD
```

Final RAM conclusion:

```text
The memory issue was resolved by physical reseating/repositioning.
The server now has the intended balanced 64 GB physical RAM layout, exposed to Linux as approximately 62 GiB usable memory.
```

Follow-up server evidence:

```text
/srv/cybervpn-h/evidence/hardware/post-ram-reseat-success-20260509T183701Z.txt
```

RAM stress test before Phase 12:

```text
UTC start: 20260509T184042Z
UTC finish: 20260509T190043Z
Tool: stress-ng
Command: numactl --interleave=all stress-ng --vm 1 --vm-bytes 48G --vm-keep --verify --timeout 20m --metrics-brief
Duration: 20m 0.51s
Result: passed
Exit code: 0
```

Observed under load:

```text
Stress RSS: ~50,334,480 KB
Swap used: 0B
NUMA anonymous huge pages:
  node0: 24576 MB
  node1: 24576 MB
RAS summary during/final:
  No Memory errors.
  No PCIe AER errors.
  No Extlog errors.
  No MCE errors.
```

Post-test state:

```text
Memory returned to idle: 62 GiB total, 60 GiB free/available
Swap used: 0B
ssh: active
caddy: active
fail2ban: active
docker: active
ufw: active
Caddy edge health: ok
```

RAM stress evidence directory:

```text
/srv/cybervpn-h/evidence/hardware/ram-stress-48g-20260509T184042Z
```
