# hooks/hook-depthai.py
#
# PyInstaller hook for the depthai package (Luxonis OAK cameras).
# No upstream hook exists in pyinstaller-hooks-contrib (as of 2026-05).
#
# depthai ships:
#   - Python extension module  (depthai.cpython-*.so / .pyd)
#   - C++ shared libraries     (libdepthai-core.so, libusb-*, …)
#   - MyriadX firmware blobs   (*.mvcmd  inside depthai/resources/)
#   - JSON schema files        (resources/schema/*.json)
#
# All of these are required at runtime.

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    logger,
)

hiddenimports = collect_submodules("depthai")

# Firmware blobs (.mvcmd) and JSON schemas — must travel with the binary
datas = collect_data_files(
    "depthai",
    includes=["**/*.mvcmd", "**/*.json", "**/*.cmd", "**/*.bin"],
)

# Native shared libraries bundled inside the wheel
binaries = collect_dynamic_libs("depthai")

if not datas and not binaries:
    logger.warning(
        "hook-depthai: no data files or binaries found. "
        "depthai may not be installed, or it is an unusually packaged wheel."
    )
else:
    logger.info(
        "hook-depthai: collected %d data file(s), %d binar(ies)",
        len(datas),
        len(binaries),
    )
