import os
import shutil

# config
NDK_PATH: str = "/Users/ricardito/Library/Android/sdk/ndk/29.0.14206865"
API: str = "21"
HOST: str = "darwin-x86_64"
STATIC_BUILD: bool = True
FFMPEG_VERSION: str = "8.0.1"
EXTERNAL_LIB_BUILD_TYPE: str = "Release"

# library versions
LIBAOM_VERSION: str = "3.13.1"
AMF_VERSION: str = "1.5.0"

# external libraries for ffmpeg
EXTERNAL_LIBS: list[str] = [
    "libaom",
    "amf"
]

pkg_config_paths: list[str] = []

toolchain_path: str = os.path.join(NDK_PATH, "toolchains", "llvm", "prebuilt", HOST)

# passed to ./configure
CONFIGURE_FLAGS: list[str] = [
    # required by android building
    "--target-os=android",
    "--enable-cross-compile",
    "--nm=" + os.path.join(toolchain_path, "bin", "llvm-nm"),
    "--ar=" + os.path.join(toolchain_path, "bin", "llvm-ar"),
    "--sysroot=" + os.path.join(toolchain_path, "sysroot"),
    "--ranlib=" + os.path.join(toolchain_path, "bin", "llvm-ranlib"),
    "--strip=" + os.path.join(toolchain_path, "bin", "llvm-strip"),
    "--pkg-config=\"pkg-config\""
]

if STATIC_BUILD:
    CONFIGURE_FLAGS.append("--enable-static")
    CONFIGURE_FLAGS.append("--disable-shared")
    CONFIGURE_FLAGS.append("--pkg-config-flags=--static")
else:
    CONFIGURE_FLAGS.append("--disable-static")
    CONFIGURE_FLAGS.append("--enable-shared")

# added to configure flags in ffmpeg()
C_FLAGS: list[str] = ["-O3", "-fPIC"]
LD_FLAGS: list[str] = ["-Wl,-z,max-page-size=16384"]

# ABIS to Build for
ABIS: list[list[str]] = [
    # [
    #     "--arch=arm",
    #     "--cross-prefix=arm-linux-androideabi-",
    #     "--cc=" + os.path.join(toolchain_path, "bin", f"armv7a-linux-androideabi{API}-clang"),
    #     "--cxx=" + os.path.join(toolchain_path, "bin", f"armv7a-linux-androideabi{API}-clang++"),
    # ],
    # [
    #     "--arch=aarch64",
    #     "--cross-prefix=aarch64-linux-android-",
    #     "--cc=" + os.path.join(toolchain_path, "bin", f"aarch64-linux-android{API}-clang"),
    #     "--cxx=" + os.path.join(toolchain_path, "bin", f"aarch64-linux-android{API}-clang++"),
    # ],
    # [
    #     "--arch=x86",
    #     "--cross-prefix=i686-linux-android-",
    #     "--cc=" + os.path.join(toolchain_path, "bin", f"i686-linux-android{API}-clang"),
    #     "--cxx=" + os.path.join(toolchain_path, "bin", f"i686-linux-android{API}-clang++"),
    #     "--disable-asm",
    #     "--x86asmexe=" + os.path.join(toolchain_path, "bin", "yasm")
    # ],
    [
        "--arch=x86_64",
        "--cross-prefix=x86_64-linux-android-",
        "--cc=" + os.path.join(toolchain_path, "bin", f"x86_64-linux-android{API}-clang"),
        "--cxx=" + os.path.join(toolchain_path, "bin", f"x86_64-linux-android{API}-clang++"),
    ]
]

CWD: str = os.getcwd()


# armeabi-v7a, arm64-v8a, x86, x86_64
def android_arch_abi_name(abi: list[str]) -> str:
    match abi[0]:
        case "--arch=arm":
            return "armeabi-v7a"
        case "--arch=aarch64":
            return "arm64-v8a"
        case "--arch=x86":
            return "x86"
        case "--arch=x86_64":
            return "x86_64"

    return ""


# armv7, arm64, x86, x86_64
def libaom_arch_abi_name(abi: list[str]) -> str:
    match abi[0]:
        case "--arch=arm":
            return "armv7"
        case "--arch=aarch64":
            return "arm64"
        case "--arch=x86":
            return "x86"
        case "--arch=x86_64":
            return "x86_64"

    return ""


def build_using_cmake(abi_name: str, lib_name: str, build_directory: str, install_directory: str, source_directory: str, specific_flags: list[str] | None = None) -> None:
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
        "-DCMAKE_C_COMPILER=clang",
        "-DCMAKE_CXX_COMPILER=clang++",
        f"-DCMAKE_BUILD_TYPE={EXTERNAL_LIB_BUILD_TYPE}",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON"
    ]

    if specific_flags is not None:
        cmake_commands.extend(specific_flags)

    if STATIC_BUILD:
        cmake_commands.append("-DBUILD_SHARED_LIBS=OFF")
    else:
        cmake_commands.append("-DBUILD_SHARED_LIBS=ON")

    print(f"Configuring {lib_name} for {abi_name} using cmake")
    if os.system(" ".join(cmake_commands)) != 0:
        raise ChildProcessError(f"CMake configure failed for {lib_name} ({abi_name})")

    print(f"Building {lib_name} for {abi_name} at {build_directory} using cmake")
    if os.system(f"cmake --build {build_directory} -- -j4") != 0:
        raise ChildProcessError(f"Build failed for {lib_name} ({abi_name})")

    print(f"Installing {lib_name} for {abi_name} to {install_directory} using cmake")
    if os.system(f"cmake --install {build_directory}") != 0:
        raise ChildProcessError(f"Install failed for {lib_name} ({abi_name})")

    print(f"Configured, Built, and Installed {lib_name} for {abi_name}")

    # tell compiler and linker of ffmpeg where to look for this library's headers and libs, and tell pkg-config where to check for .pc files
    C_FLAGS.append(f"-I{install_directory}/include")
    LD_FLAGS.append(f"-L{install_directory}/lib")
    pkg_config_paths.append(os.path.join(install_directory, "lib", "pkgconfig"))


def main():
    check_dependencies()
    libraries()
    ffmpeg()

def check_dependencies():
    if os.system("pkg-config --version") != 0:
        print("pkg-config is needed to build ffmpeg")

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
            case _:
                raise RuntimeError(f"Unsupported External Library: {lib}")

    # add licencing flags if needed
    if v3:
        if input("License must be upgraded to v3 to continue. Continue? [y/n]").strip().lower() == "n":
            print("Cannot continue, user refused to upgrade license to v3")
            exit(1)

        CONFIGURE_FLAGS.append("--enable-version3")

    if gpl:
        if input("License must be upgraded to gpl to continue. Continue? [y/n]").strip().lower() == "n":
            print("Cannot continue, user refused to upgrade license to gpl")
            exit(2)

        CONFIGURE_FLAGS.append("--enable-gpl")


def libaom() -> None:
    source_directory: str = os.path.join(CWD, "source", "libaom")

    # get source code if it's not alr there
    if not os.path.exists(source_directory):
        print(f"Cloning libaom source code at v{LIBAOM_VERSION}")
        if os.system(f"git clone --branch v{LIBAOM_VERSION} https://aomedia.googlesource.com/aom {source_directory}") != 0:
            raise ChildProcessError("git clone of libaom failed")

    # loop through abis to build
    for abi in ABIS:
        android_abi_name: str = android_arch_abi_name(abi)
        libaom_abi_name: str = libaom_arch_abi_name(abi)

        build_directory: str = os.path.join(CWD, "build", android_abi_name, "libaom")
        install_directory: str = os.path.join(CWD, "install", android_abi_name, "libaom")

        build_using_cmake(android_abi_name, "libaom", build_directory, install_directory, source_directory, [
            "-DENABLE_EXAMPLES=OFF",
            "-DENABLE_TESTS=OFF",
            "-DENABLE_TOOLS=OFF",
            "-DENABLE_DOCS=OFF",
            f"-DAOM_TARGET_CPU={libaom_abi_name}"
        ])

    CONFIGURE_FLAGS.append("--enable-libaom")


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
    C_FLAGS.append(f"-I{os.path.join(CWD, "install", "all_architectures")}")
    CONFIGURE_FLAGS.append("--enable-amf")


def ffmpeg() -> None:
    source_directory = os.path.join(CWD, "source", "ffmpeg")

    # get ffmpeg source code if not alr there
    if not os.path.exists(source_directory):
        print(f"Cloning ffmpeg source code at n{FFMPEG_VERSION}")
        if os.system(f"git clone --branch n{FFMPEG_VERSION} git@github.com:FFmpeg/FFmpeg.git {source_directory}") != 0:
            raise ChildProcessError("git clone of ffmpeg failed")

    # add C_FLAGS and LD_FLAGS to config_flags
    CONFIGURE_FLAGS.append("--extra-cflags=\"" + " ".join(C_FLAGS) + "\"")
    CONFIGURE_FLAGS.append("--extra-ldflags=\"" + " ".join(LD_FLAGS) + "\"")

    # build for each abi
    for abi in ABIS:
        abi_name: str = android_arch_abi_name(abi)

        build_directory: str = os.path.join(CWD, "build", abi_name, "ffmpeg")
        install_directory: str = os.path.join(CWD, "install", abi_name, "ffmpeg")

        # CONFIGURE_FLAGS + abi-specific configure flags
        abi_specific_config_flags: list[str] = CONFIGURE_FLAGS + abi

        # install-directory for this abi
        abi_specific_config_flags.append(f"--prefix={install_directory}")

        if not os.path.exists(build_directory):
            print(f"Making build directory for ffmpeg for {abi_name} at {build_directory}")
            os.makedirs(build_directory)

        os.chdir(build_directory)

        configure_directory = f"{source_directory}/configure"
        flags = " ".join(abi_specific_config_flags)
        paths = ":".join(pkg_config_paths)

        # tell pkg-config where to look
        os.putenv("PKG_CONFIG_PATH", f"{paths}:{os.getenv("PKG_CONFIG_PATH")}")

        print(f"Configuring ffmpeg for {abi_name}")
        if os.system(f"{configure_directory} " + flags) != 0:
            raise ChildProcessError(f"failed to configure ffmpeg with flags: " + "\n".join(abi_specific_config_flags))

        print(f"Making ffmpeg for {abi_name} at {build_directory}")
        if os.system("make -j4") != 0:
            raise ChildProcessError(f"failed to build ffmpeg for {abi_name}")

        print(f"Installing ffmpeg for {abi_name} to {install_directory}")
        if os.system("make install") != 0:
            raise ChildProcessError(f"failed to install ffmpeg for {abi_name}")

        print(f"Finished Configuring, Making, Installing ffmpeg for {abi_name}")

    print("Success, ffmpeg was built/installed for all enabled abis")


if __name__ == "__main__":
    main()
