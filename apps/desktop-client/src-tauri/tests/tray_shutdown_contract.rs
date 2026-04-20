use desktop_client_lib::engine::shell::DesktopShellState;

#[test]
fn hidden_launch_starts_in_hidden_to_tray_state() {
    let shell_state = DesktopShellState::new(true);
    let snapshot = shell_state.snapshot();

    assert_eq!(snapshot.state, "hidden-to-tray");
    assert!(!snapshot.window_visible);
    assert!(!snapshot.is_quitting);
}

#[test]
fn shutdown_transition_is_idempotent() {
    let shell_state = DesktopShellState::new(false);

    assert!(shell_state.begin_shutdown());
    assert!(!shell_state.begin_shutdown());
    assert!(shell_state.is_shutdown_in_progress());
    assert!(!shell_state.is_exit_ready());
}

#[test]
fn exit_ready_is_recorded_after_shutdown_begins() {
    let shell_state = DesktopShellState::new(false);

    assert!(shell_state.begin_shutdown());
    shell_state.mark_exit_ready();

    assert!(shell_state.is_shutdown_in_progress());
    assert!(shell_state.is_exit_ready());
}
