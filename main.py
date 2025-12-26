import os
import shutil

# things to set
NDK_PATH: str = "/Users/ricardito/Library/Android/sdk/ndk/29.0.14206865"
API: str = "21"
HOST: str = "darwin-x86_64"
STATIC_BUILD: bool = True
FFMPEG_VERSION: str = "8.0.1"
EXTERNAL_LIB_BUILD_TYPE: str = "Release"

CWD: str = os.getcwd()

LIBAOM_VERSION: str = "3.13.1"

EXTERNAL_LIBS: list[str] = [
    "libaom",
    "chromaprint",
    "libcodec2",
    "libdav1d",
    "libdavs2",
    "libuavs3d",
    "libgme",
    "libkvazaar",
    "libmp3lame",
    "liblcevc-dec",
    "libilbc",
    "libjxl",
    "libvpx",
    "libmodplug"
    "libopencore-amrnb",
    "libvo-amrwbenc",
    "libmpeghdec",
    "liblc3",
    "libopenh264",
    "librav1e",
    "libsvtav1",
    "libsvtjpegxs",
    "libtwolame",
    "libx264",
    "libx265",
    "libxavs"
    "libxavs2"
    "libxeve",
    "libxevd",
    "libzvbi"
]

is_gpl: bool = False

toolchain_path: str = os.path.join(NDK_PATH, "toolchains", "llvm", "prebuilt", HOST)

# passed to ./configure
CONFIGURE_FLAGS: list[str] = [
    # required by android building
    "--target-os=android",
    "--enable-cross-compile",
    "--nm=" + os.path.join(toolchain_path, "bin", "llvm-nm"),
    "--ar=" + os.path.join(toolchain_path, "bin", "llvm-ar"),
    "--as=" + os.path.join(toolchain_path, "bin", "llvm-as"),
    "--sysroot=" + os.path.join(toolchain_path, "sysroot"),
    "--ranlib=" + os.path.join(toolchain_path, "bin", "llvm-ranlib"),
    "--strip=" + os.path.join(toolchain_path, "bin", "llvm-strip"),
    ]

C_FLAGS: list[str] = []
LD_FLAGS: list[str] = []

if STATIC_BUILD:
    CONFIGURE_FLAGS.append("--enable-static")
    CONFIGURE_FLAGS.append("--disable-shared")
else:
    CONFIGURE_FLAGS.append("--disable-static")
    CONFIGURE_FLAGS.append("--enable-shared")

# ABIS to Build for
ABIS: list[list[str]] = [
    [
        "--arch=arm",
        "--cpu=armv7-a",
        "--cc=" + os.path.join(toolchain_path, "bin", f"armv7a-linux-androideabi{API}-clang"),
        "--cxx=" + os.path.join(toolchain_path, "bin", f"armv7a-linux-androideabi{API}-clang++"),
        ],
    [
        "--arch=aarch64",
        "--cpu=armv8-a",
        "--cc=" + os.path.join(toolchain_path, "bin", f"aarch64-linux-android{API}-clang"),
        "--cxx=" + os.path.join(toolchain_path, "bin", f"aarch64-linux-android{API}-clang++"),
        ],
    [
        "--arch=x86",
        "--cpu=i686",
        "--cc=" + os.path.join(toolchain_path, "bin", f"i686-linux-android{API}-clang"),
        "--cxx=" + os.path.join(toolchain_path, "bin", f"i686-linux-android{API}-clang++"),
        "--disable-asm",
        "--x86asmexe=" + os.path.join(toolchain_path, "bin", "yasm")
    ],
    [
        "--arch=x86_64",
        "--cpu=x86-64",
        "--cc=" + os.path.join(toolchain_path, "bin", f"x86_64-linux-android{API}-clang"),
        "--cxx=" + os.path.join(toolchain_path, "bin", f"x86_64-linux-android{API}-clang++"),
        ]
]


def get_abi_name(abi: list[str]):
    match abi[1]:
        case "--cpu=armv7-a":
            return "armeabi-v7a"
        case "--cpu=armv8-a":
            return "arm64-v8a"
        case "--cpu=i686":
            return "x86"
        case "--cpu=x86-64":
            return "x86_64"

    return ""

def build_using_cmake(abi_name: str, lib_name: str, build_directory: str, install_directory: str, source_directory: str, specific_flags: list[str] | None = None):
    global C_FLAGS
    global LD_FLAGS

    cmake_commands: list[str] = [
        "cmake",
        f"-S {source_directory}",
        f"-B {build_directory}",
        "-DCMAKE_SYSTEM_NAME=Android",
        f"-DCMAKE_ANDROID_NDK={NDK_PATH}",
        f"-DCMAKE_ANDROID_ARCH_ABI={abi_name}",
        f"-DCMAKE_ANDROID_API={API}",
        f"-DCMAKE_INSTALL_PREFIX={install_directory}",
        "-DCMAKE_C_COMPILER=clang",
        "-DCMAKE_CXX_COMPILER=clang++",
        f"-DCMAKE_BUILD_TYPE={EXTERNAL_LIB_BUILD_TYPE}"
    ]

    if specific_flags is not None:
        cmake_commands += specific_flags

    if STATIC_BUILD:
        cmake_commands.append("-DBUILD_SHARED_LIBS=OFF")
    else:
        cmake_commands.append("-DBUILD_SHARED_LIBS=ON")

    if os.system(" ".join(cmake_commands)) != 0:
        raise ChildProcessError(f"CMake configure failed for {lib_name} ({abi_name})")

    if os.system(f"cmake --build {build_directory}") != 0:
        raise ChildProcessError(f"Build failed for {lib_name} ({abi_name})")

    if os.system(f"cmake --install {build_directory}") != 0:
        raise ChildProcessError(f"Install failed for {lib_name} ({abi_name})")

    C_FLAGS += f"-I{install_directory}/include"
    LD_FLAGS += f"-L{install_directory}/lib"

def do_libaom(abi_name: str):
    build_directory: str = os.path.join(CWD, "build", abi_name, "aom")
    install_directory: str = os.path.join(CWD, "install", abi_name, "aom")
    source_directory: str = os.path.join(CWD, "aom")

    # get source code if its not alr there
    if not os.path.exists(source_directory):
        if os.system(f"git clone --branch v{LIBAOM_VERSION} https://aomedia.googlesource.com/aom {source_directory}") != 0:
            raise ChildProcessError("git clone of aom failed")

    build_using_cmake(abi_name, "aom", build_directory, install_directory, source_directory)

def do_library_stuff():
    global CONFIGURE_FLAGS

    v3: bool = False
    gpl: bool = False

    for abi in ABIS:
        abi_name: str = get_abi_name(abi)
        for lib in EXTERNAL_LIBS:
            match lib:
                case "libaom":
                    do_libaom(abi_name)

                case _:
                    raise RuntimeError(f"Unsupported Library: {lib}")

    if v3:
        CONFIGURE_FLAGS.append("--enable-version3")

    if gpl:
        CONFIGURE_FLAGS.append("--enable-gpl")


def do_ffmpeg_stuff():
    # remove ffmpeg if its alr there from a past build
    shutil.rmtree("FFmpeg")

    # first download ffmpeg source code
    if os.system(f"git clone --branch n{FFMPEG_VERSION} git@github.com:FFmpeg/FFmpeg.git") != 0:
        raise ChildProcessError("git clone of ffmpeg failed")

    os.chdir(CWD)
    os.chdir(os.path.join(CWD, "build"))

    for abi in ABIS:
        abi_name: str = get_abi_name(abi)

        os.mkdir(abi_name)
        os.chdir(abi_name)

        modified_configure_flags: list[str] = CONFIGURE_FLAGS + abi

        print(f"Configuring for {abi_name} with configure flags: {"\n".join(modified_configure_flags)}")

        flags: str = " ".join(modified_configure_flags)
        if os.system("./../../configure " + flags) != 0:
            raise ChildProcessError(f"failed to configure ffmpeg with flags: " + "\n".join(modified_configure_flags))

        print(f"Finished configuring for {abi_name}")
        print(f"Building for {abi_name}")

        if os.system("make -j") != 0:
            raise ChildProcessError(f"failed to build for {abi_name}")

        os.chdir("../")


def main():
    # remove build dir if its alr there from a past build
    shutil.rmtree(os.path.join(CWD, "build"))

    # make build directory
    os.mkdir(os.path.join(CWD, "build"))

    do_library_stuff()
    do_ffmpeg_stuff()

if __name__ == "__main__":
    main()
