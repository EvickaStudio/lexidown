"""Build the conversion engine and its bundled HTML parser together."""

import os
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, setup

port = "windows_nt" if os.name == "nt" else "posix"
vendor = Path("vendor/lexbor/source/lexbor")
sources = [
    str(path)
    for path in sorted(vendor.rglob("*.c"))
    if "ports" not in path.parts or port in path.parts
]

setup(
    ext_modules=cythonize(
        [
            Extension(
                "lexidown._native",
                ["src/lexidown/_native.pyx", *sources],
                include_dirs=["vendor/lexbor/source"],
                define_macros=[("LEXBOR_STATIC", None)],
                extra_compile_args=["/O2"] if os.name == "nt" else ["-O3", "-std=c99"],
            )
        ],
        compiler_directives={
            "language_level": 3,
            "binding": True,
            "embedsignature": True,
            "annotation_typing": False,
        },
        build_dir="build/cython",
    )
)
