use base64::{engine::general_purpose, Engine as _};
use flate2::read::GzDecoder;
use serde::Deserialize;
use serde_json::{json, Map as JsonMap, Value as JsonValue};
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
    build_lexeme_bundle(&manifest_dir, &out_dir).expect("failed to build lexeme bundle");
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
    let manifest: PipelineManifest = serde_json::from_str(&manifest_text)
        .map_err(|err| io::Error::new(ErrorKind::InvalidData, err))?;
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
            AssetKind::Compressed => {
                stage_compressed_asset(manifest_dir, out_dir, &asset.name, asset.staged_name())?
            }
        }
    }

    Ok(())
}

fn emit_rerun_if_changed(path: &Path) -> io::Result<()> {
    if path.is_file() {
        println!("cargo:rerun-if-changed={}", path.display());
        return Ok(());
    }

    if path.is_dir() {
        for entry in fs::read_dir(path)? {
            let entry = entry?;
            emit_rerun_if_changed(&entry.path())?;
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
    let canonical_repo_asset = manifest_dir
        .join("../../src/glitchlings/assets")
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

    emit_rerun_if_changed(&canonical_repo_asset)?;

    fs::create_dir_all(out_dir)?;
    let staged_target = out_dir.join(asset_name);
    if canonical_repo_asset.is_dir() {
        copy_directory(&canonical_repo_asset, &staged_target)?;
    } else {
        if let Some(parent) = staged_target.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::copy(&canonical_repo_asset, staged_target)?;
    }
    Ok(())
}

fn stage_compressed_asset(
    manifest_dir: &Path,
    out_dir: &Path,
    asset_name: &str,
    output_name: &str,
) -> io::Result<()> {
    let canonical_repo_asset = manifest_dir
        .join("../../src/glitchlings/assets")
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

    emit_rerun_if_changed(&canonical_repo_asset)?;

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
    let output_path = out_dir.join(output_name);
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)?;
    }

    let mut output = File::create(output_path)?;
    io::copy(&mut decoder, &mut output)?;
    Ok(())
}

fn copy_directory(source: &Path, target: &Path) -> io::Result<()> {
    if target.exists() {
        fs::remove_dir_all(target)?;
    }
    fs::create_dir_all(target)?;

    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let path = entry.path();
        let destination = target.join(entry.file_name());

        if path.is_dir() {
            copy_directory(&path, &destination)?;
        } else {
            if let Some(parent) = destination.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(&path, &destination)?;
        }
    }

    Ok(())
}

fn build_lexeme_bundle(manifest_dir: &Path, out_dir: &Path) -> io::Result<()> {
    let lexeme_dir = manifest_dir.join("../../src/glitchlings/assets/lexemes");
    if !lexeme_dir.is_dir() {
        return Err(io::Error::new(
            ErrorKind::NotFound,
            format!(
                "missing lexeme directory; expected {}",
                lexeme_dir.display()
            ),
        ));
    }

    emit_rerun_if_changed(&lexeme_dir)?;

    let mut bundle: JsonMap<String, JsonValue> = JsonMap::new();
    bundle.insert(
        "_meta".to_string(),
        json!({
            "version": "1.2.0",
            "description": "Bundled lexeme dictionaries for Jargoyle drift operations (generated from assets/lexemes/*.json)",
            "format": "Each file under assets/lexemes corresponds to one dictionary; keys map to arrays of replacements."
        }),
    );

    let mut entries: Vec<PathBuf> = fs::read_dir(&lexeme_dir)?
        .filter_map(|entry| entry.ok().map(|e| e.path()))
        .filter(|path| path.extension().map_or(false, |ext| ext == "json"))
        .collect();
    entries.sort();

    for path in entries {
        let file_stem = path
            .file_stem()
            .and_then(|stem| stem.to_str())
            .map(|stem| stem.to_ascii_lowercase())
            .ok_or_else(|| {
                io::Error::new(
                    ErrorKind::InvalidData,
                    format!("invalid lexeme file name {}", path.display()),
                )
            })?;

        let contents = fs::read_to_string(&path)?;
        let value: JsonValue = serde_json::from_str(&contents)
            .map_err(|err| io::Error::new(ErrorKind::InvalidData, err))?;
        bundle.insert(file_stem, value);
    }

    fs::create_dir_all(out_dir)?;
    let output_path = out_dir.join("lexemes.json");
    let rendered = serde_json::to_string(&bundle)
        .map_err(|err| io::Error::new(ErrorKind::InvalidData, err))?;
    fs::write(&output_path, rendered)?;
    Ok(())
}
