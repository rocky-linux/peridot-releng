#  -- peridot-releng-header-v0.1 --
#  Copyright (c) Peridot-Releng Authors. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#  this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  3. Neither the name of the copyright holder nor the names of its contributors
#  may be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.

from dataclasses import dataclass
from enum import Enum


class PeridotCatalogSyncPackageType(str, Enum):
    PACKAGE_TYPE_NORMAL = "PACKAGE_TYPE_NORMAL"
    PACKAGE_TYPE_NORMAL_FORK = "PACKAGE_TYPE_NORMAL_FORK"
    PACKAGE_TYPE_NORMAL_SRC = "PACKAGE_TYPE_NORMAL_SRC"
    PACKAGE_TYPE_MODULE_FORK = "PACKAGE_TYPE_MODULE_FORK"
    PACKAGE_TYPE_MODULE_FORK_COMPONENT = "PACKAGE_TYPE_MODULE_FORK_COMPONENT"
    PACKAGE_TYPE_NORMAL_FORK_MODULE = "PACKAGE_TYPE_NORMAL_FORK_MODULE"
    PACKAGE_TYPE_NORMAL_FORK_MODULE_COMPONENT = (
        "PACKAGE_TYPE_NORMAL_FORK_MODULE_COMPONENT"
    )
    PACKAGE_TYPE_MODULE_FORK_MODULE_COMPONENT = (
        "PACKAGE_TYPE_MODULE_FORK_MODULE_COMPONENT"
    )


@dataclass
class PeridotCatalogSyncRepository:
    name: str
    include_filter: list[str]
    multilib: list[str]
    module_streams: list[str]

    def module_streams_to_prototxt(self):
        return "\n" + "\n".join(
            [f'    module_stream: "{f}"' for f in self.module_streams]
        )

    def include_filter_to_prototxt(self):
        return "\n" + "\n".join(
            [f'    include_filter: "{f}"' for f in self.include_filter]
        )

    def multilib_to_prototxt(self):
        return "\n" + "\n".join([f'    multilib: "{f}"' for f in self.multilib])


@dataclass
class PeridotCatalogSyncPackage:
    name: str
    type: PeridotCatalogSyncPackageType
    repositories: list[PeridotCatalogSyncRepository]

    def repos_to_prototxt(self):
        return "\n".join(
            [
                f"""  repository {{
    name: \"{repo.name}\"{
            repo.module_streams_to_prototxt() if repo.module_streams else ""
            }{
            repo.include_filter_to_prototxt() if repo.include_filter else ""
            }{
            repo.multilib_to_prototxt() if repo.multilib else ""
            }
  }}"""
                for repo in self.repositories
            ]
        )


class PeridotCatalogSync:
    additional_multilib: list[str] = []
    exclude_multilib_filter: list[str] = []
    exclude_filter: list[tuple[str, dict]] = []
    include_filter: list[tuple[str, dict]] = []
    packages: list[PeridotCatalogSyncPackage] = []
    module_defaults = None
    major = 0
    minor = 0

    def add_package(self, package: PeridotCatalogSyncPackage):
        self.packages.append(package)

    def module_profile_to_prototxt(self, profile):
        return "\n".join([f"            name: \"{p}\"" for p in profile])

    def module_defaults_profiles_to_prototxt(self, profiles):
        if not profiles:
            return ""
        return "\n" + "\n".join(
            [f"""        profile {{
            stream: \"{f}\"
{self.module_profile_to_prototxt(profiles[f])}
        }}
""" for f in profiles.keys()]
        )

    def module_defaults_to_prototxt(self):
        return "\n".join(
            [f"""    default {{
        name: \"{f["data"]["module"]}\"
        stream: \"{f["data"].get("stream", "")}\"{
        self.module_defaults_profiles_to_prototxt(f["data"].get("profiles", []))
}    }}""" for f in self.module_defaults]
        ) if self.module_defaults else ""

    def module_configuration_to_prototxt(self):
        if not self.module_defaults:
            return ""
        return f"""module_configuration {{
    platform {{
        major: {self.major}
        minor: {self.minor}
        patch: 0
    }}
{self.module_defaults_to_prototxt()}
}}"""

    def additional_multilib_to_prototxt(self):
        return "\n" + "\n".join(
            [f'additional_multilib: "{f}"' for f in self.additional_multilib]
        )

    def exclude_multilib_filter_to_prototxt(self):
        return "\n" + "\n".join(
            [f'exclude_multilib_filter: "{f}"' for f in self.exclude_multilib_filter]
        )

    def filter_arch_to_prototxt(self, arch: dict):
        nl = "\n"
        glob_match = {}
        for k, v in arch.items():
            glob_match[k] = [f'    glob_match: "{f}"' for f in v]
        for k in glob_match.keys():
            if len(glob_match[k]) > 0:
                glob_match[k][0] = "\n" + glob_match[k][0]
        return "\n".join(
            [
                f"""  arch {{
    key: \"{f}\"{nl.join(glob_match[f])}
  }}"""
                for f in arch.keys()
            ]
        )

    def exclude_filter_to_prototxt(self):
        return "\n" + "\n".join(
            [
                f"""exclude_filter {{
  repo_match: \"{f[0]}\"
{self.filter_arch_to_prototxt(f[1])}
}}"""
                for f in self.exclude_filter
            ]
        )

    def include_filter_to_prototxt(self):
        return "\n" + "\n".join(
            [
                f"""include_filter {{
  repo_match: \"{f[0]}\"
{self.filter_arch_to_prototxt(f[1])}
}}"""
                for f in self.include_filter
            ]
        )

    def to_prototxt(self):
        ret = f"""# kind: resf.peridot.v1.CatalogSync
{self.module_configuration_to_prototxt()}{
        self.additional_multilib_to_prototxt()
        }{
        self.exclude_multilib_filter_to_prototxt()
        }{
        self.exclude_filter_to_prototxt()
        }{
        self.include_filter_to_prototxt()
        }
"""
        for pkg in self.packages:
            ret += f"""package {{
  name: "{pkg.name}"
  type: {pkg.type}
{pkg.repos_to_prototxt()}
}}
"""

        return ret
