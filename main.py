import shutil
import subprocess

from abi import ABI
from dependencies import check_cmake, check_mason, check_pkg_config, check_gawk
from constants import *
import os

library_flags: list[str] = []

def build_using_cmake(abi: ABI, lib_name: str, build_directory: str, install_directory: str, source_directory: str, specific_flags: list[str] | None = None, pkg_config_paths: list[str] | None = None) -> None:
    abi_name: str = abi.android_arch_abi_name()

    cmake_commands: list[str] = [
        "cmake",
        f"-S {source_directory}",
        f"-B {build_directory}",
        f"-DCMAKE_TOOLCHAIN_FILE={NDK_PATH}/build/cmake/android.toolchain.cmake",
        "-DCMAKE_SYSTEM_NAME=Android",
        f"-DCMAKE_ANDROID_NDK={NDK_PATH}",
        f"-DANDROID_ABI={abi_name}",
        f"-DANDROID_PLATFORM=android-{API}",
        f"-DCMAKE_ANDROID_ARCH_ABI={abi_name}",
        f"-DCMAKE_ANDROID_API={API}",
        f"-DCMAKE_INSTALL_PREFIX={install_directory}",
        f"-DCMAKE_BUILD_TYPE={EXTERNAL_LIB_BUILD_TYPE}",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON"
    ]

    if specific_flags is not None:
        cmake_commands.extend(specific_flags)

    if STATIC_BUILD:
        cmake_commands.append("-DBUILD_SHARED_LIBS=OFF")
    else:
        cmake_commands.append("-DBUILD_SHARED_LIBS=ON")

    env = os.environ.copy()

    if pkg_config_paths is not None:
        env["PKG_CONFIG_PATH"] = ":".join(pkg_config_paths)

    print(f"Configuring {lib_name} for {abi_name} using cmake")
    subprocess.run(cmake_commands, env=env, check=True)

    print(f"Building {lib_name} for {abi_name} at {build_directory} using cmake")
    subprocess.run(["cmake", "--build", build_directory, "-j"], check=True)

    print(f"Installing {lib_name} for {abi_name} to {install_directory} using cmake")
    subprocess.run(["cmake", "--install", build_directory], check=True)

    print(f"Configured, Built, and Installed {lib_name} for {abi_name} using cmake")

    # tell compiler and linker of ffmpeg where to look for this library's headers and libs, and tell pkg-config where to check for .pc files
    abi.c_flags.append(f"-I{install_directory}/include")
    abi.ld_flags.append(f"-L{install_directory}/lib")
    abi.pkg_config_paths.append(os.path.join(install_directory, "lib", "pkgconfig"))


def build_using_meson(abi: ABI, lib_name: str, build_directory: str, install_directory: str, source_directory: str, specific_flags: list[str] | None = None, pkg_config_paths: list[str] | None = None) -> None:
    gen_meson_files()

    cross_file = f"android-{NDK_VERSION}-"

    abi_name = abi.android_arch_abi_name()

    match abi_name:
        case "armeabi-v7a":
            cross_file += f"androideabi{API}-armv7a-cross.txt"
        case "arm64-v8a":
            cross_file += f"android{API}-aarch64-cross.txt"
        case "x86":
            cross_file += f"android{API}-i686-cross.txt"
        case "x86_64":
            cross_file += f"android{API}-x86_64-cross.txt"

    meson_commands: list[str] = [
        "meson",
        "setup",
        f"--prefix={install_directory}",
        f"--cross-file={os.path.join(CWD, "build", "meson_cross_files", cross_file)}",
        f"--buildtype={EXTERNAL_LIB_BUILD_TYPE.lower()}",
        "--reconfigure"
    ]

    if STATIC_BUILD:
        meson_commands.append("--default-library=static")
    else:
        meson_commands.append("--default-library=shared")

    if specific_flags is not None:
        meson_commands.extend(specific_flags)

    meson_commands.extend([
        build_directory,
        source_directory
    ])

    env = os.environ.copy()

    if pkg_config_paths is not None:
        env["PKG_CONFIG_PATH"] = ":".join(pkg_config_paths)

    print(f"Setting up {lib_name} for {abi_name} using meson")
    subprocess.run(meson_commands, env=env, check=True)

    os.chdir(build_directory)

    print(f"Compiling {lib_name} for {abi_name} at {build_directory} using meson")
    subprocess.run(["meson", "compile"], check=True)

    print(f"Installing {lib_name} for {abi_name} to {install_directory} using meson")
    subprocess.run(["meson", "install"], check=True)

    print(f"Setup, Compiled, and Installed {lib_name} for {abi_name} using meson")

    # tell compiler and linker of ffmpeg where to look for this library's headers and libs, and tell pkg-config where to check for .pc files
    abi.c_flags.append(f"-I{install_directory}/include")
    abi.ld_flags.append(f"-L{install_directory}/lib")
    abi.pkg_config_paths.append(os.path.join(install_directory, "lib", "pkgconfig"))


def gen_meson_files() -> None:
    if os.system(f"meson env2mfile -o {os.path.join(CWD, "build", "meson_cross_files")} --android") != 0:
        raise ChildProcessError("Could not make meson android cross files")


def main():
    check_pkg_config()
    ffmpeg_libs()
    libraries()
    ffmpeg()


def ffmpeg_libs() -> None:
    source_directory = os.path.join(CWD, "source", "ffmpeg")

    # get ffmpeg source code if not alr there
    if not os.path.exists(source_directory):
        print(f"Cloning ffmpeg source code at n{FFMPEG_VERSION}")
        if os.system(f"git clone --branch n{FFMPEG_VERSION} git@github.com:FFmpeg/FFmpeg.git {source_directory}") != 0:
            raise ChildProcessError("git clone of ffmpeg failed")

    # build for each abi
    for abi in ABIS:
        abi_name: str = abi.android_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", abi_name, "ffmpeg")
        install_directory: str = os.path.join(CWD, "install", abi_name, "ffmpeg")
        configure_directory = f"{source_directory}/configure"

        flags: list[str] = [
                               configure_directory,
                               "--target-os=android",
                               "--enable-cross-compile",
                               "--nm=" + os.path.join(toolchain_path, "bin", "llvm-nm"),
                               "--ar=" + os.path.join(toolchain_path, "bin", "llvm-ar"),
                               "--sysroot=" + os.path.join(toolchain_path, "sysroot"),
                               "--ranlib=" + os.path.join(toolchain_path, "bin", "llvm-ranlib"),
                               "--strip=" + os.path.join(toolchain_path, "bin", "llvm-strip"),
                               "--pkg-config=pkg-config",
                               "--extra-libs=-lc++",
                               f"--prefix={install_directory}",
                               "--disable-programs"
                           ] + abi.command()

        if STATIC_BUILD:
            flags.extend([
                "--enable-static",
                "--disable-shared",
                "--pkg-config-flags=--static"
            ])
        else:
            flags.extend([
                "--disable-static",
                "--enable-shared",
                "--pkg-config-flags=--static"
            ])

        if not os.path.exists(build_directory):
            print(f"Making build directory for ffmpeg for {abi_name} at {build_directory}")
            os.makedirs(build_directory)

        os.chdir(build_directory)

        print(f"Configuring ffmpeg libs for {abi_name}")
        subprocess.run(flags, check=True)

        print(f"Making ffmpeg libs for {abi_name} at {build_directory}")
        subprocess.run(["make", "-j"], check=True)

        print(f"Installing ffmpeg libs for {abi_name} to {install_directory}")
        subprocess.run(["make", "install"], check=True)

        print(f"Finished Configuring, Making, Installing ffmpeg libs for {abi_name}")

    print("Success, ffmpeg libs was built/installed for all enabled abis")


def libraries() -> None:
    v3: bool = False
    gpl: bool = False

    # loop through libraries, calling its function
    for lib in EXTERNAL_LIBS:
        match lib:
            case "libaom":
                libaom()
            case "amf":
                amf()
            case "avisynth":
                avisynth()
                gpl = True
            case "chromaprint":
                chromaprint()
            case "libcodec2":
                libcodec2()
            case "libdav1d":
                libdav1d()
            case "libuavs3d":
                libuavs3d()
            case _:
                raise RuntimeError(f"Unsupported External Library: {lib}")

    # add licencing flags if needed
    if v3:
        if input("License must be upgraded to v3 to continue. Continue? [y/n]: ").strip().lower() == "n":
            print("Cannot continue, user refused to upgrade license to v3")
            exit(1)

        library_flags.append("--enable-version3")

    if gpl:
        if input("License must be upgraded to gpl to continue. Continue? [y/n]: ").strip().lower() == "n":
            print("Cannot continue, user refused to upgrade license to gpl")
            exit(2)

        library_flags.append("--enable-gpl")


def libaom() -> None:
    check_cmake()
    source_directory: str = os.path.join(CWD, "source", "libaom")

    # get source code if it's not alr there
    if not os.path.exists(source_directory):
        print(f"Cloning libaom source code at v{LIBAOM_VERSION}")
        if os.system(f"git clone --branch v{LIBAOM_VERSION} https://aomedia.googlesource.com/aom {source_directory}") != 0:
            raise ChildProcessError("git clone of libaom failed")

    # loop through abis to build
    for abi in ABIS:
        android_abi_name: str = abi.android_arch_abi_name()
        libaom_abi_name: str = abi.libaom_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", android_abi_name, "libaom")
        install_directory: str = os.path.join(CWD, "install", android_abi_name, "libaom")

        build_using_cmake(abi, "libaom", build_directory, install_directory, source_directory, [
            "-DENABLE_EXAMPLES=OFF",
            "-DENABLE_TESTS=OFF",
            "-DENABLE_TOOLS=OFF",
            "-DENABLE_DOCS=OFF",
            f"-DAOM_TARGET_CPU={libaom_abi_name}",
            "-DCONFIG_PIC=1"
        ])

    library_flags.append("--enable-libaom")


def amf() -> None:
    source_directory = os.path.join(CWD, "source", "amf")

    # get ffmpeg source code if not alr there
    if not os.path.exists(source_directory):
        print(f"Cloning amf source code at v{AMF_VERSION}")
        if os.system(f"git clone --branch v{AMF_VERSION} git@github.com:GPUOpen-LibrariesAndSDKs/AMF.git {source_directory}") != 0:
            raise ChildProcessError("git clone of amf failed")

    install_directory = os.path.join(CWD, "install", "all_architectures", "AMF")

    print("Making install directory for amf")
    os.makedirs(install_directory, exist_ok=True)

    print("Copying amf headers to install directory")
    shutil.copytree(src=os.path.join(source_directory, "amf", "public", "include"), dst=install_directory, dirs_exist_ok=True)

    print("Finished 'installing' amf")
    # put c_flags for all abis
    for abi in ABIS:
        abi.c_flags.append(f"-I{os.path.join(CWD, "install", "all_architectures")}")

    library_flags.append("--enable-amf")


def avisynth() -> None:
    check_cmake()
    source_directory = os.path.join(CWD, "source", "avisynth")

    if not os.path.exists(source_directory):
        print(f"Cloning avisynth source code at v{AVISYNTH_VERSION}")
        if os.system(f"git clone --branch v{AVISYNTH_VERSION} git@github.com:AviSynth/AviSynthPlus.git {source_directory}") != 0:
            raise ChildProcessError("git clone of avisynth failed")

    # loop through abis to build
    for abi in ABIS:
        android_abi_name = abi.android_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", android_abi_name, "avisynth")
        install_directory: str = os.path.join(CWD, "install", android_abi_name, "avisynth")

        if android_abi_name == "x86_64":
            build_using_cmake(abi, "avisynth", build_directory, install_directory, source_directory, [
                "-DENABLE_PLUGINS=OFF",
                "-DENABLE_CUDA=OFF",
                "-DENABLE_INTEL_SIMD=ON"
            ])
        else:
            build_using_cmake(abi, "avisynth", build_directory, install_directory, source_directory, [
                "-DENABLE_PLUGINS=OFF",
                "-DENABLE_CUDA=OFF",
                "-DENABLE_INTEL_SIMD=OFF"
            ])

    library_flags.append("--enable-avisynth")


def chromaprint() -> None:
    check_cmake()
    source_directory = os.path.join(CWD, "source", "chromaprint")

    if not os.path.exists(source_directory):
        print(f"Cloning chromaprint source code at v{CHROMAPRINT_VERSION}")
        if os.system(f"git clone --branch v{CHROMAPRINT_VERSION} git@github.com:acoustid/chromaprint.git {source_directory}") != 0:
            raise ChildProcessError("git clone of chromaprint failed")

    # loop through abis to build
    for abi in ABIS:
        android_abi_name = abi.android_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", android_abi_name, "chromaprint")
        install_directory: str = os.path.join(CWD, "install", android_abi_name, "chromaprint")

        build_using_cmake(abi, "chromaprint", build_directory, install_directory, source_directory, [
            "-DBUILD_TOOLS=OFF",
            "-DBUILD_TESTS=OFF",
            "-DBUILD_EXAMPLES=OFF",
            f"-DKISSFFT_SOURCE_DIR={os.path.join(source_directory, "src", "3rdparty", "kissfft")}",
        ])

    library_flags.append("--enable-chromaprint")


def libcodec2() -> None:
    check_cmake()
    source_directory = os.path.join(CWD, "source", "libcodec2")

    if not os.path.exists(source_directory):
        print(f"Cloning libcodec2 source code at {LIBCODEC2_VERSION}")
        if os.system(f"git clone --branch {LIBCODEC2_VERSION} git@github.com:drowe67/codec2.git {source_directory}") != 0:
            raise ChildProcessError("git clone of libcodec2 failed")

    # loop through abis to build
    for abi in ABIS:
        android_abi_name = abi.android_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", android_abi_name, "libcodec2")
        install_directory: str = os.path.join(CWD, "install", android_abi_name, "libcodec2")

        build_using_cmake(abi, "libcodec2", build_directory, install_directory, source_directory, [
            "-DUNITTEST=OFF"
        ])

    library_flags.append("--enable-libcodec2")


def libdav1d() -> None:
    check_mason()
    source_directory = os.path.join(CWD, "source", "libdav1d")

    if not os.path.exists(source_directory):
        print(f"Cloning libdav1d source code at {LIBDAV1D_VERSION}")
        if os.system(f"git clone --branch {LIBDAV1D_VERSION} https://code.videolan.org/videolan/dav1d.git {source_directory}") != 0:
            raise ChildProcessError("git clone of libdav1d failed")

    # loop through abis to build
    for abi in ABIS:
        android_abi_name = abi.android_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", android_abi_name, "libdav1d")
        install_directory: str = os.path.join(CWD, "install", android_abi_name, "libdav1d")

        build_using_meson(abi, "libdav1d", build_directory, install_directory, source_directory, [
            "-Dlogging=false",
            "-Denable_tools=false"
        ])

    library_flags.append("--enable-libdav1d")


def libuavs3d() -> None:
    check_gawk()
    source_directory = os.path.join(CWD, "source", "libuavs3d")

    if not os.path.exists(source_directory):
        print(f"Cloning libuavs3d source code at v{LIBUAVS3_VERSION}")
        if os.system(f"git clone --branch v{LIBUAVS3_VERSION} git@github.com:rbaucells/uavs3d.git {source_directory}") != 0:
            raise ChildProcessError("git clone of libuavs3d failed")

    if os.system(os.path.join(source_directory, "version.sh")) != 0:
        raise ChildProcessError(f"libuavs3d version.sh in {source_directory} failed")

    # loop through abis to build
    for abi in ABIS:
        android_abi_name = abi.android_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", android_abi_name, "libuavs3d")
        install_directory: str = os.path.join(CWD, "install", android_abi_name, "libuavs3d")

        build_using_cmake(abi, "libuavs3d", build_directory, install_directory, source_directory, [
            "-DCOMPILE_10BIT=1",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ])


def ffmpeg() -> None:
    source_directory = os.path.join(CWD, "source", "ffmpeg")

    # get ffmpeg source code if not alr there
    if not os.path.exists(source_directory):
        print(f"Cloning ffmpeg source code at n{FFMPEG_VERSION}")
        if os.system(f"git clone --branch n{FFMPEG_VERSION} git@github.com:FFmpeg/FFmpeg.git {source_directory}") != 0:
            raise ChildProcessError("git clone of ffmpeg failed")

    # build for each abi
    for abi in ABIS:
        abi_name: str = abi.android_arch_abi_name()

        build_directory: str = os.path.join(CWD, "build", abi_name, "ffmpeg")
        install_directory: str = os.path.join(CWD, "install", abi_name, "ffmpeg")
        configure_directory = f"{source_directory}/configure"

        flags: list[str] = [
                               configure_directory,
                               "--target-os=android",
                               "--enable-cross-compile",
                               "--nm=" + os.path.join(toolchain_path, "bin", "llvm-nm"),
                               "--ar=" + os.path.join(toolchain_path, "bin", "llvm-ar"),
                               "--sysroot=" + os.path.join(toolchain_path, "sysroot"),
                               "--ranlib=" + os.path.join(toolchain_path, "bin", "llvm-ranlib"),
                               "--strip=" + os.path.join(toolchain_path, "bin", "llvm-strip"),
                               "--pkg-config=pkg-config",
                               "--extra-libs=-lc++",
                               f"--prefix={install_directory}"
                           ] + abi.command()

        if STATIC_BUILD:
            flags.extend([
                "--enable-static",
                "--disable-shared",
                "--pkg-config-flags=--static"
            ])
        else:
            flags.extend([
                "--disable-static",
                "--enable-shared"
            ])

        if not os.path.exists(build_directory):
            print(f"Making build directory for ffmpeg for {abi_name} at {build_directory}")
            os.makedirs(build_directory)

        os.chdir(build_directory)

        env = os.environ.copy()

        if abi.pkg_config_paths is not None:
            env["PKG_CONFIG_PATH"] = ":".join(abi.pkg_config_paths)

        print(f"Configuring ffmpeg for {abi_name}")
        subprocess.run(flags, env=env, check=True)

        print(f"Making ffmpeg for {abi_name} at {build_directory}")
        subprocess.run(["make", "-j"], check=True)

        print(f"Installing ffmpeg for {abi_name} to {install_directory}")
        subprocess.run(["make", "install"], check=True)

        print(f"Finished Configuring, Making, Installing ffmpeg for {abi_name}")

    print("Success, ffmpeg was built/installed for all enabled abis")


if __name__ == "__main__":
    main()
