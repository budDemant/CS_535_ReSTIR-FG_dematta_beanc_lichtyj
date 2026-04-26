import os
import sys

# Tell Falcor's pybind11 module to skip PluginManager::loadAllPlugins() on import.
# getRuntimeDirectory() on Linux resolves relative to /proc/self/exe, which is
# packman's python here, not Mogwai, so plugins/plugins.json doesn't exist and
# nlohmann::json::parse() throws parse_error.101 during module init. We only
# need the pybind11 bindings for stub generation, not the plugins themselves.
os.environ["FALCOR_EMBEDDED_PYTHON"] = "1"

from pybind11_stubgen import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise RuntimeError(
            "One argument expected: the falcor python library directory."
        )
    package_dir = sys.argv[1]
    main(["-o", package_dir, "--ignore-invalid=all", "--skip-signature-downgrade", "--no-setup-py", "--root-module-suffix=", "falcor"])
