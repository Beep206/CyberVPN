use ns_testkit::{UdpWanLabCommandKind, udp_wan_lab_profiles};

fn main() {
    println!("Northstar UDP WAN lab profiles:");
    for profile in udp_wan_lab_profiles() {
        let spec_ids = profile.spec_suite_ids.join(", ");
        let fallback_rule = if profile.requires_no_silent_fallback {
            "no silent fallback after datagram selection"
        } else {
            "explicit fallback remains visible"
        };
        println!(
            "- {slug} [{spec_ids}] -> cargo test {command}\n  {description}; {fallback_rule}",
            slug = profile.slug,
            spec_ids = spec_ids,
            command = render_command(
                profile.command_kind,
                profile.command_selector,
                profile.cargo_args
            ),
            description = profile.description,
            fallback_rule = fallback_rule,
        );
    }
}

fn render_command(
    command_kind: UdpWanLabCommandKind,
    command_selector: &str,
    cargo_args: &[&str],
) -> String {
    let args = cargo_args.join(" ");
    match command_kind {
        UdpWanLabCommandKind::LiveUdp => format!("{args}  # live_udp:{command_selector}"),
        UdpWanLabCommandKind::Lib => format!("{args}  # lib:{command_selector}"),
    }
}
