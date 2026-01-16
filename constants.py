import os
from argparse import Namespace
import argparse
from pathlib import Path

from abi import ABI


def get_args() -> Namespace:
    parser = argparse.ArgumentParser(description="Python script to help in building ffmpeg and related external libraries for android")

    parser.add_argument("--android_ndk_version", type=str, help="", default=None)
    parser.add_argument("--android_ndk_path", type=str, help="", default=None)
    parser.add_argument("--android_api", type=str, help="", default=None)
    parser.add_argument("--android_ndk_host", type=str, help="", default=None)
    parser.add_argument("--static_build", type=str, help="", default=None)
    parser.add_argument("--external_lib_build_type", type=str, help="", default=None)

    parser.add_argument("--ffmpeg_version", type=str, default=None)
    parser.add_argument("--libaom_version", type=str, default=None)
    parser.add_argument("--amf_version", type=str, default=None)
    parser.add_argument("--avisynth_version", type=str, default=None)
    parser.add_argument("--chromaprint_version", type=str, default=None)
    parser.add_argument("--libcodec2_version", type=str, default=None)
    parser.add_argument("--libdav1d_version", type=str, default=None)
    parser.add_argument("--libuavs3_version", type=str, default=None)
    parser.add_argument("--libdavs2_version", type=str, default=None)

    return parser.parse_args()


def get_option(arg: str | None, env_var_name: str, default: str) -> str:
    if arg is not None:
        return arg
    elif env_var_name in os.environ:
        return os.environ[env_var_name]
    else:
        return default


args = get_args()

# -------------------- CONFIG -------------------
NDK_VERSION: str = get_option(args.android_ndk_version, "ANDROID_NDK_VERSION", "29.0.14206865")
NDK_PATH: str = get_option(args.android_ndk_path, "ANDROID_NDK_PATH", os.path.join(Path.home(), "Library", "Android", "sdk", "ndk", NDK_VERSION))

API: str = get_option(args.android_api, "ANDROID_API", "28")
HOST: str = get_option(args.android_ndk_host, "ANDROID_NDK_HOST", "darwin-x86_64")

STATIC_BUILD: bool = get_option(args.static_build, "STATIC_BUILD", "true").lower() in {"true", "1", "on", "yes", "y"}

EXTERNAL_LIB_BUILD_TYPE: str = get_option(args.external_lib_build_type, "EXTERNAL_LIB_BUILD_TYPE", "Release")

# lib version
FFMPEG_VERSION: str = get_option(args.ffmpeg_version, "FFMPEG_VERSION", "8.0.1")
LIBAOM_VERSION: str = get_option(args.libaom_version, "LIBAOM_VERSION", "3.13.1")
AMF_VERSION: str = get_option(args.amf_version, "AMF_VERSION", "1.5.0")
AVISYNTH_VERSION: str = get_option(args.avisynth_version, "AVISYNTH_VERSION", "3.7.5")
CHROMAPRINT_VERSION: str = get_option(args.chromaprint_version, "CHROMAPRINT_VERSION", "1.6.0")
LIBCODEC2_VERSION: str = get_option(args.libcodec2_version, "LIBCODEC2_VERSION", "1.2.0")
LIBDAV1D_VERSION: str = get_option(args.libdav1d_version, "LIBDAV1D_VERSION", "1.5.3")
LIBUAVS3_VERSION: str = get_option(args.libuavs3_version, "LIBUAVS3_VERSION", "1.2")
LIBDAVS2_VERSION: str = get_option(args.libdavs2_version, "LIBDAVS2_VERSION", "1.7")

# external libraries for ffmpeg (libdavs2 and libuavs3d are currently broken)
EXTERNAL_LIBS: list[str] = [
    "libaom",
    "amf",
    "avisynth",
    "chromaprint",
    "libcodec2",
    "libdav1d",
    "libuavs3d",
    "libdavs2"
]

toolchain_path: str = os.path.join(NDK_PATH, "toolchains", "llvm", "prebuilt", HOST)

CWD: str = os.getcwd()

# ABIS to Build for
ABIS: list[ABI] = [
    ABI("arm", "arm-linux-androideabi-", os.path.join(toolchain_path, "bin", f"armv7a-linux-androideabi{API}-clang"), os.path.join(toolchain_path, "bin", f"armv7a-linux-androideabi{API}-clang++")),
    ABI("aarch64", "aarch64-linux-android-", os.path.join(toolchain_path, "bin", f"aarch64-linux-android{API}-clang"), os.path.join(toolchain_path, "bin", f"aarch64-linux-android{API}-clang++")),
    ABI("x86", "i686-linux-android-", os.path.join(toolchain_path, "bin", f"i686-linux-android{API}-clang"), os.path.join(toolchain_path, "bin", f"i686-linux-android{API}-clang++"), ["--disable-asm", f"--x86asmexe={os.path.join(toolchain_path, "bin", "yasm")}"]),
    ABI("x86_64", "x86_64-linux-android-", os.path.join(toolchain_path, "bin", f"x86_64-linux-android{API}-clang"), os.path.join(toolchain_path, "bin", f"x86_64-linux-android{API}-clang++"))
]