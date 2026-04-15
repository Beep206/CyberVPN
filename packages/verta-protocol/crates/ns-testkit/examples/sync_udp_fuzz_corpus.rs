use ns_testkit::repo_root;
use serde::Deserialize;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Deserialize)]
struct HexFixture {
    hex: String,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root = repo_root();
    let fuzz_root = root.join("fuzz").join("cargo-fuzz");

    sync_seed_group(
        &root,
        &fuzz_root,
        "corpus/control_frame_decoder",
        &[
            "wire/v1/valid/NS-FX-PING-001.json",
            "wire/v1/valid/NS-FX-HELLO-001.json",
            "wire/v1/valid/NS-FX-HELLO-NOOVERLAP-002.json",
            "wire/v1/valid/NS-FX-UDP-OPEN-001.json",
            "wire/v1/valid/NS-FX-UDP-OK-001.json",
            "wire/v1/valid/NS-FX-UDP-OK-FALLBACK-002.json",
            "wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-001.json",
            "wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-DGRAMUNAVAIL-002.json",
            "wire/v1/valid/NS-FX-UDP-FLOW-CLOSE-PROTOVIOL-003.json",
            "wire/v1/invalid/WC-HELLO-TRUNCATED-001.json",
            "wire/v1/invalid/WC-HELLO-MINMAX-002.json",
            "wire/v1/invalid/WC-HELLO-EMPTYTOKEN-003.json",
            "wire/v1/invalid/WC-PING-NONCANONVARINT-004.json",
            "wire/v1/invalid/WC-HELLO-BADCARRIER-005.json",
            "wire/v1/invalid/WC-UDP-OPEN-RESERVEDFLAGS-007.json",
            "wire/v1/invalid/WC-UDP-OPEN-TRUNCATED-020.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONFLOW-034.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONFLAGS-035.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONTIMEOUT-036.json",
            "wire/v1/invalid/WC-UDP-OPEN-IPV4LEN-038.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADTARGETTYPE-039.json",
            "wire/v1/invalid/WC-UDP-OPEN-IPV6LEN-040.json",
            "wire/v1/invalid/WC-UDP-OPEN-EMPTYDOMAIN-041.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONTARGETTYPE-043.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONPORT-044.json",
            "wire/v1/invalid/WC-UDP-OPEN-ZEROPORT-047.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADUTF8DOMAIN-048.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADMETACOUNT-056.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONMETACOUNT-057.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADMETALEN-065.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONMETALEN-061.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONMETATYPE-069.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONFRAMELEN-073.json",
            "wire/v1/invalid/WC-UDP-OK-BADMODE-009.json",
            "wire/v1/invalid/WC-UDP-OK-TRUNCATED-018.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONPAYLOAD-029.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONFLOW-030.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONTIMEOUT-037.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMODE-042.json",
            "wire/v1/invalid/WC-UDP-OK-ZEROMAXPAYLOAD-049.json",
            "wire/v1/invalid/WC-UDP-OK-ZEROIDLETIMEOUT-051.json",
            "wire/v1/invalid/WC-UDP-OK-BADMETACOUNT-055.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMETACOUNT-058.json",
            "wire/v1/invalid/WC-UDP-OK-BADMETALEN-066.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMETALEN-062.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMETATYPE-070.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONFRAMELEN-074.json",
            "wire/v1/invalid/WC-UDP-OK-BADFRAMELEN-085.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADFRAMELEN-086.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADCODE-012.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONCODE-024.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFLOW-032.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADFRAMELEN-084.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADUTF8-052.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-TRUNCATED-016.json",
        ],
    )?;
    sync_seed_group(
        &root,
        &fuzz_root,
        "corpus/udp_datagram_decoder",
        &[
            "wire/v1/valid/NS-FX-UDP-DGRAM-001.json",
            "wire/v1/valid/NS-FX-UDP-DGRAM-MTU-002.json",
            "wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLOW-021.json",
            "wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLAGS-027.json",
            "wire/v1/invalid/WC-UDP-DGRAM-RESERVEDFLAGS-008.json",
            "wire/v1/invalid/WC-UDP-DGRAM-TRUNCATED-015.json",
        ],
    )?;
    sync_seed_group(
        &root,
        &fuzz_root,
        "corpus/udp_fallback_frame_decoder",
        &[
            "wire/v1/valid/NS-FX-UDP-STREAM-OPEN-001.json",
            "wire/v1/valid/NS-FX-UDP-STREAM-ACCEPT-001.json",
            "wire/v1/valid/NS-FX-UDP-STREAM-PACKET-001.json",
            "wire/v1/valid/NS-FX-UDP-STREAM-CLOSE-001.json",
            "wire/v1/valid/NS-FX-UDP-STREAM-CLOSE-IDLE-002.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-LEN-010.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-BADFRAMELEN-080.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-011.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-022.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONCODE-028.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFLOW-033.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADFRAMELEN-083.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADUTF8-050.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-TRUNCATED-017.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-TRUNCATED-019.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETALEN-068.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-TRUNCATED-013.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFLOW-025.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETACOUNT-053.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETALEN-067.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETALEN-063.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-BADFRAMELEN-081.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONLEN-031.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-TRUNCATED-014.json",
        ],
    )?;

    sync_seed_group(
        &root,
        &fuzz_root,
        "fuzz_regressions/control_frame_decoder",
        &[
            "wire/v1/invalid/WC-HELLO-TRUNCATED-001.json",
            "wire/v1/invalid/WC-HELLO-MINMAX-002.json",
            "wire/v1/invalid/WC-HELLO-EMPTYTOKEN-003.json",
            "wire/v1/invalid/WC-PING-NONCANONVARINT-004.json",
            "wire/v1/invalid/WC-HELLO-BADCARRIER-005.json",
            "wire/v1/invalid/WC-UDP-OPEN-RESERVEDFLAGS-007.json",
            "wire/v1/invalid/WC-UDP-OPEN-TRUNCATED-020.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONFLOW-034.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONFLAGS-035.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONTIMEOUT-036.json",
            "wire/v1/invalid/WC-UDP-OPEN-IPV4LEN-038.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADTARGETTYPE-039.json",
            "wire/v1/invalid/WC-UDP-OPEN-IPV6LEN-040.json",
            "wire/v1/invalid/WC-UDP-OPEN-EMPTYDOMAIN-041.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONTARGETTYPE-043.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONPORT-044.json",
            "wire/v1/invalid/WC-UDP-OPEN-ZEROPORT-047.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADUTF8DOMAIN-048.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADMETACOUNT-056.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONMETACOUNT-057.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADMETALEN-065.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONMETALEN-061.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONMETATYPE-069.json",
            "wire/v1/invalid/WC-UDP-OPEN-NONCANONFRAMELEN-073.json",
            "wire/v1/invalid/WC-UDP-OK-BADMODE-009.json",
            "wire/v1/invalid/WC-UDP-OK-TRUNCATED-018.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONPAYLOAD-029.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONFLOW-030.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONTIMEOUT-037.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMODE-042.json",
            "wire/v1/invalid/WC-UDP-OK-ZEROMAXPAYLOAD-049.json",
            "wire/v1/invalid/WC-UDP-OK-ZEROIDLETIMEOUT-051.json",
            "wire/v1/invalid/WC-UDP-OK-BADMETACOUNT-055.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMETACOUNT-058.json",
            "wire/v1/invalid/WC-UDP-OK-BADMETALEN-066.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMETALEN-062.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONMETATYPE-070.json",
            "wire/v1/invalid/WC-UDP-OK-NONCANONFRAMELEN-074.json",
            "wire/v1/invalid/WC-UDP-OK-BADFRAMELEN-085.json",
            "wire/v1/invalid/WC-UDP-OPEN-BADFRAMELEN-086.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADCODE-012.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONCODE-024.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFLOW-032.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADFRAMELEN-084.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-BADUTF8-052.json",
            "wire/v1/invalid/WC-UDP-FLOW-CLOSE-TRUNCATED-016.json",
        ],
    )?;
    sync_seed_group(
        &root,
        &fuzz_root,
        "fuzz_regressions/udp_datagram_decoder",
        &[
            "wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLOW-021.json",
            "wire/v1/invalid/WC-UDP-DGRAM-NONCANONFLAGS-027.json",
            "wire/v1/invalid/WC-UDP-DGRAM-RESERVEDFLAGS-008.json",
            "wire/v1/invalid/WC-UDP-DGRAM-TRUNCATED-015.json",
        ],
    )?;
    sync_seed_group(
        &root,
        &fuzz_root,
        "fuzz_regressions/udp_fallback_frame_decoder",
        &[
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-011.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADCODE-022.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONCODE-028.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFLOW-033.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADFRAMELEN-083.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-BADUTF8-050.json",
            "wire/v1/invalid/WC-UDP-STREAM-CLOSE-TRUNCATED-017.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-TRUNCATED-019.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADMETALEN-068.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076.json",
            "wire/v1/invalid/WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-LEN-010.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONLEN-031.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-BADFRAMELEN-080.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-TRUNCATED-013.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFLOW-025.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETACOUNT-053.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-BADMETALEN-067.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETALEN-063.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075.json",
            "wire/v1/invalid/WC-UDP-STREAM-OPEN-BADFRAMELEN-081.json",
            "wire/v1/invalid/WC-UDP-STREAM-PACKET-TRUNCATED-014.json",
        ],
    )?;

    println!("UDP fuzz corpus and regression seeds synchronized.");
    Ok(())
}

fn sync_seed_group(
    root: &Path,
    fuzz_root: &Path,
    relative_dir: &str,
    fixtures: &[&str],
) -> Result<(), Box<dyn std::error::Error>> {
    let dir = fuzz_root.join(relative_dir);
    fs::create_dir_all(&dir)?;

    for fixture in fixtures {
        let bytes = decode_fixture_hex(&root.join("fixtures").join(fixture))?;
        let filename = Path::new(fixture)
            .file_stem()
            .expect("fixture should have a file stem")
            .to_string_lossy()
            .into_owned();
        fs::write(dir.join(format!("{filename}.bin")), bytes)?;
    }

    Ok(())
}

fn decode_fixture_hex(path: &PathBuf) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let fixture: HexFixture = serde_json::from_str(&fs::read_to_string(path)?)?;
    Ok(hex::decode(fixture.hex)?)
}
