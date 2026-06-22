//! Native macOS integration (Phase 11.8): haptic feedback + asset:// path safety.
//!
//! Two independent surfaces live here because both are the "native" half of 11.8:
//!  - `haptic` — a Tauri command performing a macOS NSHapticFeedback pattern.
//!  - `resolve_asset_path` — the BLOCKING security chokepoint for the asset://
//!    scheme: it canonicalizes a requested path against an allowlisted root and
//!    rejects anything that escapes it (traversal, absolute paths, symlink hops).

use std::path::{Component, Path, PathBuf};

/// Perform a named haptic pattern. Always `Ok` — haptics are additive feedback,
/// never required for function, so a missing device or non-mac platform is a
/// silent no-op, not an error the UI must handle.
#[tauri::command]
pub fn haptic(pattern: String) -> Result<(), String> {
    perform_haptic(&pattern);
    Ok(())
}

#[cfg(target_os = "macos")]
fn perform_haptic(pattern: &str) {
    use objc2_app_kit::{
        NSHapticFeedbackManager, NSHapticFeedbackPattern, NSHapticFeedbackPerformanceTime,
        NSHapticFeedbackPerformer,
    };
    let ns_pattern = match pattern {
        "success" => NSHapticFeedbackPattern::LevelChange,
        "warn" => NSHapticFeedbackPattern::Alignment,
        // "tap" and anything unknown fall back to the neutral generic bump.
        _ => NSHapticFeedbackPattern::Generic,
    };
    // ponytail: runs on the Tauri command worker thread, not the main thread. The
    // default performer is a process-global singleton and tolerates this in
    // practice; if a future macOS rejects off-main perform, hop via
    // `app.run_on_main_thread(..)`. Untestable without trackpad hardware.
    unsafe {
        let performer = NSHapticFeedbackManager::defaultPerformer();
        performer
            .performFeedbackPattern_performanceTime(ns_pattern, NSHapticFeedbackPerformanceTime::Now);
    }
}

#[cfg(not(target_os = "macos"))]
fn perform_haptic(_pattern: &str) {}

/// Resolve a requested asset path against an allowlisted root, returning the
/// canonical path only if it stays strictly inside `root`.
///
/// Defense in depth: a syntactic `..` check rejects traversal before we touch the
/// filesystem, then `canonicalize` + `starts_with` is the backstop that also
/// catches symlink escapes. Absolute paths collapse to root-relative (the leading
/// `/` is stripped), so `asset:///etc/passwd` cannot escape.
pub fn resolve_asset_path(root: &Path, requested: &str) -> Option<PathBuf> {
    let rel = requested.trim_start_matches('/');
    if Path::new(rel)
        .components()
        .any(|c| matches!(c, Component::ParentDir))
    {
        return None;
    }
    let canon_root = std::fs::canonicalize(root).ok()?;
    let canon = std::fs::canonicalize(canon_root.join(rel)).ok()?;
    canon.starts_with(&canon_root).then_some(canon)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn haptic_is_ok_for_every_pattern() {
        // No display/hardware in CI: the contract is just that the command never
        // errors, on any platform, for known or unknown patterns.
        assert!(haptic("success".into()).is_ok());
        assert!(haptic("warn".into()).is_ok());
        assert!(haptic("tap".into()).is_ok());
        assert!(haptic("totally-unknown".into()).is_ok());
    }

    #[test]
    fn resolve_asset_path_allows_files_inside_root() {
        let root = std::env::temp_dir().join(format!("acos_asset_ok_{}", std::process::id()));
        fs::create_dir_all(&root).unwrap();
        fs::write(root.join("ok.txt"), b"hi").unwrap();

        let got = resolve_asset_path(&root, "ok.txt");
        assert!(got.is_some(), "in-root file should resolve");
        assert!(got.unwrap().ends_with("ok.txt"));

        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn resolve_asset_path_rejects_traversal_and_absolute() {
        let base = std::env::temp_dir().join(format!("acos_asset_trav_{}", std::process::id()));
        let root = base.join("root");
        fs::create_dir_all(&root).unwrap();
        fs::write(base.join("secret.txt"), b"secret").unwrap();

        assert_eq!(resolve_asset_path(&root, "../secret.txt"), None);
        assert_eq!(resolve_asset_path(&root, "../../etc/passwd"), None);
        assert_eq!(resolve_asset_path(&root, "/etc/passwd"), None);
        assert_eq!(resolve_asset_path(&root, "missing.txt"), None);

        fs::remove_dir_all(&base).ok();
    }
}
