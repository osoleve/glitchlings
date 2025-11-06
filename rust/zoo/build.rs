use base64::{engine::general_purpose, Engine as _};
use flate2::read::GzDecoder;
use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::{self, File};
use std::io::{self, Cursor, ErrorKind, Read};
use std::path::PathBuf;
use std::process::Command;

fn main() {
    stage_asset("ocr_confusions.tsv").expect("failed to stage OCR confusion table for compilation");
    stage_asset("apostrofae_pairs.json")
        .expect("failed to stage Apostrofae replacement table for compilation");
    stage_asset("ekkokin_homophones.json")
        .expect("failed to stage Ekkokin homophone table for compilation");
    stage_lexicon_asset("default_vector_cache.json")
        .expect("failed to stage Jargoyle vector cache for compilation");
    stage_compressed_asset("mim1c_homoglyphs.json.gz.b64", "mim1c_homoglyphs.json")
        .expect("failed to stage Mim1c homoglyph table for compilation");
    stage_asset("hokey_assets.json").expect("failed to stage Hokey asset payload for compilation");
    pyo3_build_config::add_extension_module_link_args();

    // Only perform custom Python linking on non-Linux platforms.
    // On Linux, manylinux wheels must NOT link against libpython to ensure portability.
    // PyO3's add_extension_module_link_args() already handles this correctly by default.
    if cfg!(not(target_os = "linux")) {
        if let Some(python) = configured_python() {
            link_python(&python);
        } else if let Some(python) = detect_python() {
            link_python(&python);
        }
    }
}

fn configured_python() -> Option<OsString> {
    std::env::var_os("PYO3_PYTHON")
        .or_else(|| std::env::var_os("PYTHON"))
        .filter(|path| !path.is_empty())
}

fn detect_python() -> Option<OsString> {
    const CANDIDATES: &[&str] = &[
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
        "python",
    ];

    for candidate in CANDIDATES {
        let status = Command::new(candidate).arg("-c").arg("import sys").output();

        if let Ok(output) = status {
            if output.status.success() {
                return Some(OsString::from(candidate));
            }
        }
    }

    None
}

fn link_python(python: &OsStr) {
    if let Some(path) = query_python(
        python,
        "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')",
    ) {
        let trimmed = path.trim();
        if !trimmed.is_empty() {
            println!("cargo:rustc-link-search=native={trimmed}");
        }
    }

    if let Some(path) = query_python(
        python,
        "import sysconfig; print(sysconfig.get_config_var('LIBPL') or '')",
    ) {
        let trimmed = path.trim();
        if !trimmed.is_empty() {
            println!("cargo:rustc-link-search=native={trimmed}");
        }
    }

    if let Some(library) = query_python(
        python,
        "import sysconfig; print(sysconfig.get_config_var('LDLIBRARY') or '')",
    ) {
        let name = library.trim();
        if let Some(stripped) = name.strip_prefix("lib") {
            let stem = stripped
                .strip_suffix(".so")
                .or_else(|| stripped.strip_suffix(".a"))
                .or_else(|| stripped.strip_suffix(".dylib"))
                .unwrap_or(stripped);
            if !stem.is_empty() {
                println!("cargo:rustc-link-lib={stem}");
            }
        }
    }
}

fn query_python(python: &OsStr, command: &str) -> Option<String> {
    let output = Command::new(python).arg("-c").arg(command).output().ok()?;
    if !output.status.success() {
        return None;
    }
    let value = String::from_utf8(output.stdout).ok()?;
    Some(value)
}

fn stage_asset(asset_name: &str) -> io::Result<()> {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("missing manifest dir"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("missing OUT_DIR"));

    let canonical_repo_asset = manifest_dir.join("../../assets").join(asset_name);
    if !canonical_repo_asset.exists() {
        return Err(io::Error::new(
            ErrorKind::NotFound,
            format!(
                "missing asset {asset_name}; expected {}",
                canonical_repo_asset.display()
            ),
        ));
    }

    println!("cargo:rerun-if-changed={}", canonical_repo_asset.display());

    fs::create_dir_all(&out_dir)?;
    fs::copy(&canonical_repo_asset, out_dir.join(asset_name))?;
    Ok(())
}

fn stage_lexicon_asset(asset_name: &str) -> io::Result<()> {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("missing manifest dir"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("missing OUT_DIR"));

    let canonical_repo_asset = manifest_dir
        .join("../../src/glitchlings/lexicon/data")
        .join(asset_name);
    if !canonical_repo_asset.exists() {
        return Err(io::Error::new(
            ErrorKind::NotFound,
            format!(
                "missing asset {asset_name}; expected {}",
                canonical_repo_asset.display()
            ),
        ));
    }

    println!("cargo:rerun-if-changed={}", canonical_repo_asset.display());

    fs::create_dir_all(&out_dir)?;
    fs::copy(&canonical_repo_asset, out_dir.join(asset_name))?;
    Ok(())
}

fn stage_compressed_asset(asset_name: &str, output_name: &str) -> io::Result<()> {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("missing manifest dir"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("missing OUT_DIR"));

    let canonical_repo_asset = manifest_dir.join("../../assets").join(asset_name);
    if !canonical_repo_asset.exists() {
        return Err(io::Error::new(
            ErrorKind::NotFound,
            format!(
                "missing asset {asset_name}; expected {}",
                canonical_repo_asset.display()
            ),
        ));
    }

    println!("cargo:rerun-if-changed={}", canonical_repo_asset.display());

    fs::create_dir_all(&out_dir)?;
    let mut encoded = String::new();
    File::open(&canonical_repo_asset)?.read_to_string(&mut encoded)?;

    let stripped = encoded
        .chars()
        .filter(|ch| !ch.is_whitespace())
        .collect::<String>();

    let decoded = general_purpose::STANDARD
        .decode(stripped.as_bytes())
        .map_err(|err| io::Error::new(ErrorKind::InvalidData, err))?;

    let mut decoder = GzDecoder::new(Cursor::new(decoded));
    let mut output = File::create(out_dir.join(output_name))?;
    io::copy(&mut decoder, &mut output)?;
    Ok(())
}
