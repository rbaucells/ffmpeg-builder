import os


def check_pkg_config() -> None:
    if os.system("pkg-config --version") != 0:
        print("pkg-config is not installed")
        exit(3)


def check_cmake() -> None:
    if os.system("cmake --version") != 0:
        print("cmake is not installed")
        exit(4)


def check_mason() -> None:
    if os.system("meson --version") != 0:
        print("meson is not installed")
        exit(5)

def check_gawk() -> None:
    if os.system("gawk --version") != 0:
        print("gawk is not installed")
        exit(6)