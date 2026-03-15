use crate::engine::error::AppError;
use crate::ipc::models::ProxyNode;
use crate::engine::parser;

/// Scans all active displays for a QR code and attempts to parse it into a ProxyNode
pub async fn scan_screen_for_qr() -> Result<ProxyNode, AppError> {
    // Execute screen capture on a blocking thread since xcap blocks
    let raw_link = tokio::task::spawn_blocking(move || {
        let monitors = xcap::Monitor::all()
            .map_err(|e| AppError::System(format!("Failed to list monitors: {}", e)))?;
            
        if monitors.is_empty() {
             return Err(AppError::System("Screen capture permission denied or unsupported display server".into()));
        }

        // We iterate through all displays and try to detect a QR code
        for monitor in monitors.iter() {
            if let Ok(image) = monitor.capture_image() {
                // Convert to luma8 (grayscale)
                let dynamic_image = image::DynamicImage::ImageRgba8(image);
                let luma = dynamic_image.to_luma8();
                let width = luma.width();
                let height = luma.height();
                
                // using rxing's Luma8LuminanceSource
                let source = rxing::Luma8LuminanceSource::new(luma.into_raw(), width, height);
                let mut binarizer = rxing::common::HybridBinarizer::new(source);
                let mut bitmap = rxing::BinaryBitmap::new(binarizer);
                
                let mut decode_hints = rxing::DecodeHints::default();
                decode_hints.TryHarder = Some(true);
                decode_hints.PossibleFormats = Some(vec![rxing::BarcodeFormat::QR_CODE].into_iter().collect());
                
                let mut reader = rxing::qrcode::QRCodeReader {};
                use rxing::Reader;
                
                if let Ok(result) = reader.decode_with_hints(&mut bitmap, &decode_hints) {
                    return Ok(result.getText().to_string());
                }
            }
        }
        
        Err(AppError::System("No QR code found on any screen".to_string()))
    }).await.map_err(|e| AppError::System(format!("AsyncTask panicked: {}", e)))??;

    // Pipe the extracted string to the existing parser
    parser::parse_link(&raw_link)
}
