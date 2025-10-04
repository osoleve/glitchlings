use std::ffi::OsStr;
use std::process::Command;

fn main() {
    pyo3_build_config::add_extension_module_link_args();

    if let Some(python) = std::env::var_os("PYO3_PYTHON")
        .or_else(|| std::env::var_os("PYTHON"))
        .filter(|path| !path.is_empty())
    {
        link_python(&python);
    }
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
