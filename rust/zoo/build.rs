use std::env;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io::{self, ErrorKind};
use std::path::PathBuf;
use std::process::Command;

fn main() {
    prepare_confusion_table().expect("failed to stage OCR confusion table for compilation");
    pyo3_build_config::add_extension_module_link_args();

    if let Some(python) = configured_python() {
        link_python(&python);
    } else if let Some(python) = detect_python() {
        link_python(&python);
    }
}

fn configured_python() -> Option<OsString> {
    std::env::var_os("PYO3_PYTHON")
        .or_else(|| std::env::var_os("PYTHON"))
        .filter(|path| !path.is_empty())
}

fn detect_python() -> Option<OsString> {
    const CANDIDATES: &[&str] = &["python3.12", "python3", "python"];

    for candidate in CANDIDATES {
        let status = Command::new(candidate)
            .arg("-c")
            .arg("import sys")
            .output();

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

fn prepare_confusion_table() -> io::Result<()> {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("missing manifest dir"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("missing OUT_DIR"));

    let repo_path = manifest_dir.join("../../src/glitchlings/zoo/ocr_confusions.tsv");
    let packaged_path = manifest_dir.join("assets/ocr_confusions.tsv");
    println!("cargo:rerun-if-changed={}", packaged_path.display());

    let source_path = if repo_path.exists() {
        println!("cargo:rerun-if-changed={}", repo_path.display());
        if packaged_path.exists() {
            let repo_bytes = fs::read(&repo_path)?;
            let packaged_bytes = fs::read(&packaged_path)?;
            if repo_bytes != packaged_bytes {
                return Err(io::Error::new(
                    ErrorKind::Other,
                    format!(
                        "OCR confusion table at {} is out of sync with {}",
                        packaged_path.display(),
                        repo_path.display()
                    ),
                ));
            }
        }
        repo_path
    } else {
        if !packaged_path.exists() {
            return Err(io::Error::new(
                ErrorKind::NotFound,
                format!(
                    "missing OCR confusion table; looked for {} and {}",
                    repo_path.display(),
                    packaged_path.display()
                ),
            ));
        }
        packaged_path
    };

    fs::create_dir_all(&out_dir)?;
    fs::copy(&source_path, out_dir.join("ocr_confusions.tsv"))?;
    Ok(())
}

