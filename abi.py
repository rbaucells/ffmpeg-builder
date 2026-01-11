class ABI:
    def __init__(self, arch: str, cross_prefix: str, cc: str, cxx: str, extra_flags: list[str] | None = None):
        self.arch = arch
        self.cross_prefix = cross_prefix
        self.cc = cc
        self.cxx = cxx
        self.extra_flags = extra_flags

        self.c_flags = ["-O3", "-fPIC"]
        self.ld_flags = ["-Wl,-z,max-page-size=16384"]
        self.pkg_config_paths = []


    def command(self) -> list[str]:
        result: list[str] = [
            f"--arch={self.arch}",
            f"--cross-prefix={self.cross_prefix}",
            f"--cc={self.cc}",
            f"--cxx={self.cxx}",
            f"--extra-cflags=\"{" ".join(self.c_flags)}\"",
            f"--extra-ldflags=\"{" ".join(self.ld_flags)}\"",
            f"--extra-ldflags=\"{" ".join(self.ld_flags)}\""
        ]

        if self.extra_flags is not None:
            result.extend(self.extra_flags)

        return result

    # armeabi-v7a, arm64-v8a, x86, x86_64
    def android_arch_abi_name(self) -> str:
        match self.arch:
            case "arm":
                return "armeabi-v7a"
            case "aarch64":
                return "arm64-v8a"
            case "x86":
                return "x86"
            case "x86_64":
                return "x86_64"

        return ""

    # armv7, arm64, x86, x86_64
    def libaom_arch_abi_name(self) -> str:
        match self.arch:
            case "arm":
                return "armv7"
            case "aarch64":
                return "arm64"
            case "x86":
                return "x86"
            case "x86_64":
                return "x86_64"

        return ""