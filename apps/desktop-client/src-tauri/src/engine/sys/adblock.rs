use crate::engine::error::AppError;
use reqwest::Client;
use std::collections::HashSet;
use tauri::AppHandle;
use serde_json::json;

pub async fn download_blocklists(app_handle: &AppHandle, level: &str) -> Result<(), AppError> {
    if level == "disabled" {
        return Ok(());
    }

    let mut urls = vec![
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts", // Standard ads/malware
    ];

    if level == "strict" {
        urls.push("https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/fakenews-gambling-porn-social/hosts");
    }

    let client = Client::new();
    let mut combined_domains: HashSet<String> = HashSet::new();

    for url in urls {
        let resp = client.get(url).send().await?;
        if !resp.status().is_success() {
            return Err(AppError::System(format!("Failed to update Privacy Shield databases: HTTP {}", resp.status())));
        }
        
        let text = resp.text().await?;
        
        let domains = tokio::task::spawn_blocking(move || {
            let mut local_set = HashSet::new();
            for line in text.lines() {
                let trimmed = line.trim();
                // Ignore comments and empty lines
                if trimmed.is_empty() || trimmed.starts_with('#') {
                    continue;
                }
                
                // Hosts file format typically: 0.0.0.0 domain.com
                let mut parts = trimmed.split_whitespace();
                if let (Some(ip), Some(domain)) = (parts.next(), parts.next()) {
                    if ip == "0.0.0.0" || ip == "127.0.0.1" {
                        if domain != "0.0.0.0" && domain != "localhost" && domain != "127.0.0.1" && domain != "broadcasthost" {
                            local_set.insert(domain.to_string());
                        }
                    }
                }
            }
            local_set
        }).await.map_err(|e| AppError::System(format!("Failed to process blocklist: {}", e)))?;
        
        combined_domains.extend(domains);
    }

    let ruleset_json = json!({
        "version": 1,
        "rules": [
            {
                "domain_suffix": combined_domains,
            }
        ]
    });

    let app_dir = crate::engine::store::get_app_dir(app_handle)?;
    let bin_dir = app_dir.join("bin");
    
    if !bin_dir.exists() {
        tokio::fs::create_dir_all(&bin_dir).await.map_err(|e| AppError::System(e.to_string()))?;
    }

    let db_path = bin_dir.join("adblock-standard.json");
    let staging_path = bin_dir.join("adblock-standard.tmp");

    let json_bytes = serde_json::to_vec(&ruleset_json)?;
    
    tokio::fs::write(&staging_path, json_bytes).await?;
    tokio::fs::rename(&staging_path, &db_path).await?;
    
    Ok(())
}
