# JGINYUE X99-D8 BIOS Flash Prep Evidence

Date: 2026-05-09

Server: `cybervpn-h-ops`, `10.10.10.34`

Board: `JGINYUE X99-D8 Server V1.0`

Official source page: <https://www.jginyue.com.cn/index/Article/show/cat_id/48/id/62>

Official archive URL: <https://jginyue.com/public/upload/a7/bb95fe00af14bc611816d724accd1d.rar>

Server prep directory:

```text
/srv/cybervpn-h/evidence/hardware/bios/official-jginyue-x99-d8-flash-prep-20260509T181403Z
```

Prepared files:

```text
jginyue-x99-d8-bios.rar
J99X8002-official.bin
current-spi-before-flash.bin
ifd-bios-selected-read-test.bin
sha256sums.txt
compare-report.txt
flashrom-identify.txt
read-current-spi.log
ifd-bios-selected-read-test.log
FLASH_OFFICIAL_JGINYUE_X99_D8_BIOS_REGION.sh
```

Checksums:

```text
e591a7c2ec4c4625d49280605ee13055eac3fe0bdd149f5073e8a28f58476a31  jginyue-x99-d8-bios.rar
7232495d5cfd237aebcb36b4666bf5fa2ea492b22a806f1cdea4feca604a2781  J99X8002-official.bin
d271e60bbcfb8c36ca9b0a72bde193fd78587cbb5bf34c6a1aace5ec29ac2fd8  current-spi-before-flash.bin
```

Image identity strings found in both official image and current dump:

```text
05/14/2021
American Megatrends
J99X8002
JGINYUE
X99-D8
```

Region comparison against the official full image:

```text
full_spi: different
flash_descriptor_0x000000_0x000fff: identical
me_region_0x001000_0x7fffff: identical
bios_nvram_area_0x800000_0x87ffff: different
bios_code_area_0x880000_0xffffff: identical
```

The prepared flash mode is BIOS-region only:

```bash
flashrom -p internal --ifd -i bios -w J99X8002-official.bin
flashrom -p internal --ifd -i bios -v J99X8002-official.bin
```

When the decision is made to flash from the server console:

```bash
cd /srv/cybervpn-h/evidence/hardware/bios/official-jginyue-x99-d8-flash-prep-20260509T181403Z
sudo env FLASH_OFFICIAL_JGINYUE_X99_D8=I_UNDERSTAND_THE_RISK ./FLASH_OFFICIAL_JGINYUE_X99_D8_BIOS_REGION.sh
```

The guarded server-side script was syntax checked with `bash -n` and refuses to run unless the explicit risk-confirmation environment variable is set.

The `flashrom --ifd -i bios` read test completed successfully. The selected BIOS-region read matches the current full-chip dump in the BIOS region.

Full-chip write execution:

```text
Started UTC:   20260509T182130Z
Completed UTC: 20260509T182222Z
```

Executed command:

```bash
flashrom -p internal -w J99X8002-official.bin
```

Verification:

```text
flashrom write-stage verify: VERIFIED
separate flashrom verify:    VERIFIED
post-write readback compare: POST_WRITE_READBACK_MATCHES_OFFICIAL=yes
```

Post-write readback SHA256:

```text
7232495d5cfd237aebcb36b4666bf5fa2ea492b22a806f1cdea4feca604a2781  J99X8002-official.bin
7232495d5cfd237aebcb36b4666bf5fa2ea492b22a806f1cdea4feca604a2781  current-spi-after-full-write-20260509T182253Z.bin
```

Execution logs on server:

```text
full-chip-identify-before-20260509T182130Z.log
full-chip-read-before-20260509T182130Z.log
full-chip-write-20260509T182130Z.log
full-chip-verify-20260509T182130Z.log
full-chip-read-after-20260509T182253Z.log
full-chip-readback-compare-20260509T182253Z.txt
```

Status: full-chip official JGINYUE image was written and verified. Power-cycle is still required for the platform to boot from the flashed firmware state.
