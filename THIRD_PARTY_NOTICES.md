# MediaCraft third-party notices

MediaCraft is distributed under the GNU General Public License version 3 or later.
The full license text is included in `LICENSE` and `LICENSES/GPL-3.0.txt`.

The Windows one-folder distribution contains the following third-party software.
Copyright remains with each project and its contributors. The license files named below
are included with the distribution. This document is informational and does not replace
the license texts.

| Component | Use in MediaCraft | License | Included text / source |
| --- | --- | --- | --- |
| CPython 3.11 | Embedded Python runtime | PSF License and the Python license stack | `LICENSES/Python-3.11.txt`; <https://github.com/python/cpython/tree/3.11> |
| PySide6 / Qt / Shiboken6 6.11.1 | GUI and Qt runtime | LGPL-3.0-only, GPL, or commercial; MediaCraft uses the LGPL option | `LICENSES/LGPL-3.0.txt` and `LICENSES/GPL-3.0.txt`; <https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.11.1> and <https://code.qt.io/cgit/qt/qtbase.git/tag/?h=v6.11.1> |
| PyAV 18.0.0 | FFmpeg bindings and media analysis | BSD-3-Clause | `LICENSES/PyAV-BSD-3-Clause.txt`; <https://github.com/PyAV-Org/PyAV/tree/v18.0.0> |
| FFmpeg and codec libraries bundled by PyAV | Native media libraries in the PyAV wheel | GPL-compatible build; exact terms depend on the enabled libraries | `LICENSES/GPL-3.0.txt`; build sources: <https://github.com/PyAV-Org/pyav-ffmpeg> and <https://github.com/FFmpeg/FFmpeg> |
| python-mpv 1.0.8 | Python interface to libmpv | GPL-2.0-or-later or LGPL-2.1-or-later | `LICENSES/python-mpv-GPL.txt` and `LICENSES/python-mpv-LGPL.txt`; <https://github.com/jaseg/python-mpv> |
| mpv / libmpv and its statically linked dependencies | Playback engine | GPL-3.0-or-later for the selected shinchiro build | `LICENSES/GPL-3.0.txt`; <https://github.com/mpv-player/mpv> |
| shinchiro mpv-winbuild-cmake release 20260610 | Windows libmpv build | Individual component licenses; selected FFmpeg build enables GPL and version 3 | Build record: `vendor/mpv/BUILD.txt`; corresponding build scripts and sources: <https://github.com/shinchiro/mpv-winbuild-cmake/tree/20260610> |
| PyInstaller 6.21.0 bootloader | Windows executable bootstrap | GPL-2.0-or-later with the PyInstaller bootloader exception | `LICENSES/PyInstaller.txt`; <https://github.com/pyinstaller/pyinstaller/tree/v6.21.0> |

MediaCraft dynamically loads the separately distributed Qt and libmpv DLLs. Recipients
may replace those DLLs with compatible modified builds. MediaCraft imposes no restriction
on reverse engineering performed for debugging modifications to LGPL-covered libraries.

The complete corresponding source for MediaCraft is available at
<https://github.com/hebowiz/MediaCraft>. Source and build scripts for the native libraries
are available from the project links above. Keep the exact release archive together with
its `BUILD.txt` record when preparing a release. If a dependency or binary source changes,
review this notice and run `scripts/collect_licenses.py` again before distribution.

Python is a registered trademark of the Python Software Foundation. MediaCraft is not
affiliated with or endorsed by the Python Software Foundation, The Qt Company, the mpv
project, FFmpeg, PyAV, or PyInstaller.
