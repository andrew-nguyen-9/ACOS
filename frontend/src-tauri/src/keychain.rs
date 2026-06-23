//! Phase 16.1 (ADR-014): Keychain-backed credential storage.
//!
//! The long-lived account secret lives in the OS Keychain, never in SQLite or a
//! dotfile (ADR-014 §2). The backend sidecar only ever sees a short-lived session
//! token; this module is how the frontend stows/reads the secret so a returning
//! user can re-mint a session without re-typing it.
//!
//! `CredentialStore` is the cross-platform seam: macOS Keychain is the only impl
//! now (ADR-014 §5), Windows Credential Manager / libsecret slot in behind the same
//! trait in Phase 18 — so callers and the Tauri commands never change.

/// Service namespace under which ACOS stores credentials in the OS store.
const SERVICE: &str = "com.acos.credentials";

/// Cross-platform credential store.
pub trait CredentialStore {
    fn set(&self, account: &str, secret: &str) -> Result<(), String>;
    fn get(&self, account: &str) -> Result<Option<String>, String>;
    fn delete(&self, account: &str) -> Result<(), String>;
}

/// The (service, account) pair a backend must key on. Pure — testable without
/// touching any real credential store, and the contract Win/Linux impls share.
pub fn entry_id(account: &str) -> (&'static str, String) {
    (SERVICE, account.to_string())
}

#[cfg(target_os = "macos")]
pub struct KeychainStore;

#[cfg(target_os = "macos")]
impl CredentialStore for KeychainStore {
    fn set(&self, account: &str, secret: &str) -> Result<(), String> {
        let entry = keyring::Entry::new(SERVICE, account).map_err(|e| e.to_string())?;
        entry.set_password(secret).map_err(|e| e.to_string())
    }

    fn get(&self, account: &str) -> Result<Option<String>, String> {
        let entry = keyring::Entry::new(SERVICE, account).map_err(|e| e.to_string())?;
        match entry.get_password() {
            Ok(p) => Ok(Some(p)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(e.to_string()),
        }
    }

    fn delete(&self, account: &str) -> Result<(), String> {
        let entry = keyring::Entry::new(SERVICE, account).map_err(|e| e.to_string())?;
        match entry.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(e.to_string()),
        }
    }
}

/// Default-closed on platforms without a wired backend: a missing impl errors
/// rather than silently pretending to store a secret it dropped.
#[cfg(not(target_os = "macos"))]
pub struct KeychainStore;

#[cfg(not(target_os = "macos"))]
impl CredentialStore for KeychainStore {
    fn set(&self, _a: &str, _s: &str) -> Result<(), String> {
        Err("credential store unavailable on this platform".into())
    }
    fn get(&self, _a: &str) -> Result<Option<String>, String> {
        Err("credential store unavailable on this platform".into())
    }
    fn delete(&self, _a: &str) -> Result<(), String> {
        Err("credential store unavailable on this platform".into())
    }
}

fn store() -> KeychainStore {
    KeychainStore
}

#[tauri::command]
pub fn keychain_set(account: String, secret: String) -> Result<(), String> {
    store().set(&account, &secret)
}

#[tauri::command]
pub fn keychain_get(account: String) -> Result<Option<String>, String> {
    store().get(&account)
}

#[tauri::command]
pub fn keychain_delete(account: String) -> Result<(), String> {
    store().delete(&account)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::sync::Mutex;

    #[test]
    fn entry_id_namespaces_under_service() {
        let (service, account) = entry_id("session-token");
        assert_eq!(service, "com.acos.credentials");
        assert_eq!(account, "session-token");
    }

    /// In-memory store standing in for the real Keychain (which would prompt in
    /// CI). Proves the trait contract every platform impl must satisfy.
    struct MockStore(Mutex<HashMap<String, String>>);

    impl CredentialStore for MockStore {
        fn set(&self, account: &str, secret: &str) -> Result<(), String> {
            self.0.lock().unwrap().insert(account.into(), secret.into());
            Ok(())
        }
        fn get(&self, account: &str) -> Result<Option<String>, String> {
            Ok(self.0.lock().unwrap().get(account).cloned())
        }
        fn delete(&self, account: &str) -> Result<(), String> {
            self.0.lock().unwrap().remove(account);
            Ok(())
        }
    }

    #[test]
    fn credential_store_round_trips() {
        let store = MockStore(Mutex::new(HashMap::new()));
        assert_eq!(store.get("k").unwrap(), None); // missing → None, not error
        store.set("k", "secret").unwrap();
        assert_eq!(store.get("k").unwrap(), Some("secret".into()));
        store.delete("k").unwrap();
        assert_eq!(store.get("k").unwrap(), None);
    }
}
