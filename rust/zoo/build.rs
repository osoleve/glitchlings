use base64::{engine::general_purpose, Engine as _};
use flate2::read::GzDecoder;
use serde::Deserialize;
use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::{self, File};
use std::io::{self, Cursor, ErrorKind, Read};
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
enum AssetKind {
    Copy,
    Compressed,
}

impl Default for AssetKind {
    fn default() -> Self {
        AssetKind::Copy
    }
}

#[derive(Debug, Deserialize)]
struct AssetSpec {
    name: String,
    #[serde(default)]
    kind: AssetKind,
    output: Option<String>,
}

impl AssetSpec {
    fn staged_name(&self) -> &str {
        self.output.as_deref().unwrap_or(&self.name)
    }
}

#[derive(Debug, Deserialize)]
struct PipelineManifest {
    pipeline_assets: Vec<AssetSpec>,
}

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("missing manifest dir"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("missing OUT_DIR"));

    let manifest =
        load_pipeline_manifest(&manifest_dir).expect("failed to load pipeline asset manifest");

    stage_pipeline_assets(&manifest_dir, &out_dir, &manifest)
        .expect("failed to stage pipeline assets for compilation");
    stage_lexicon_asset(&manifest_dir, &out_dir, "default_vector_cache.json")
        .expect("failed to stage Jargoyle vector cache for compilation");
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

fn load_pipeline_manifest(manifest_dir: &Path) -> io::Result<PipelineManifest> {
    let manifest_path = manifest_dir.join("../../src/glitchlings/assets/pipeline_assets.json");
    if !manifest_path.exists() {
        return Err(io::Error::new(
            ErrorKind::NotFound,
            format!(
                "missing pipeline asset manifest; expected {}",
                manifest_path.display()
            ),
        ));
    }

    println!("cargo:rerun-if-changed={}", manifest_path.display());

    let manifest_text = fs::read_to_string(&manifest_path)?;
    let manifest: PipelineManifest =
        serde_json::from_str(&manifest_text).map_err(|err| io::Error::new(ErrorKind::InvalidData, err))?;
    Ok(manifest)
}

fn stage_pipeline_assets(
    manifest_dir: &Path,
    out_dir: &Path,
    manifest: &PipelineManifest,
) -> io::Result<()> {
    for asset in &manifest.pipeline_assets {
        match asset.kind {
            AssetKind::Copy => stage_asset(manifest_dir, out_dir, &asset.name)?,
            AssetKind::Compressed => stage_compressed_asset(
                manifest_dir,
                out_dir,
                &asset.name,
                asset.staged_name(),
            )?,
        }
    }

    Ok(())
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

fn stage_asset(manifest_dir: &Path, out_dir: &Path, asset_name: &str) -> io::Result<()> {
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

    fs::create_dir_all(out_dir)?;
    fs::copy(&canonical_repo_asset, out_dir.join(asset_name))?;
    Ok(())
}

fn stage_lexicon_asset(
    manifest_dir: &Path,
    out_dir: &Path,
    asset_name: &str,
) -> io::Result<()> {
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

    fs::create_dir_all(out_dir)?;
    fs::copy(&canonical_repo_asset, out_dir.join(asset_name))?;
    Ok(())
}

fn stage_compressed_asset(
    manifest_dir: &Path,
    out_dir: &Path,
    asset_name: &str,
    output_name: &str,
) -> io::Result<()> {
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

    fs::create_dir_all(out_dir)?;
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
