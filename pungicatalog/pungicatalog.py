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

import argparse
import os
import yaml

import kobo.conf

from catalog import (
    PeridotCatalogSync,
    PeridotCatalogSyncPackage,
    PeridotCatalogSyncPackageType,
    PeridotCatalogSyncRepository,
)
from scm import SCM

def get_modules_for_repo(package, repo, module_index):
    if not repo in module_index:
        return None

    modules = []
    for module in module_index[repo]:
        if module.startswith(f"{package}:"):
            modules.append(module.split(":")[1])

    if len(modules) == 0:
        return None

    return modules

def main(pungi_conf_path: str, output_path: str, major: int, minor: int):
    pungi_base = os.path.dirname(pungi_conf_path)
    print(f"Using pungi base: {pungi_base}")

    conf = kobo.conf.PyConfigParser()
    conf.load_from_file(pungi_conf_path)
    print(f"Loaded pungi config: {pungi_conf_path}")

    print("Loading prepopulate...")
    gather_prepopulate_scm_dict = conf.get("gather_prepopulate")
    gpscm = SCM(pungi_base, gather_prepopulate_scm_dict)
    gpjson = gpscm.json()

    # Get variants
    print("Loading variants...")
    variants_file_scm_dict = conf.get("variants_file")
    vscm = SCM(pungi_base, variants_file_scm_dict)
    vxml = vscm.xml()

    # Get module defaults
    print("Loading module defaults...")
    module_defaults_file_scm_dict = conf.get("module_defaults_dir")
    mdscm = SCM(pungi_base, module_defaults_file_scm_dict, ext_filters=[".yaml"])
    mdtexts = mdscm.texts()

    # Create a catalog
    catalog = PeridotCatalogSync()
    catalog.major = major
    catalog.minor = minor

    # Set multilib filters
    catalog.additional_multilib.extend(list(conf.get("multilib_whitelist").values())[0])
    catalog.exclude_multilib_filter.extend(
        list(conf.get("multilib_blacklist").values())[0]
    )

    # Set additional packages/filters
    catalog.exclude_filter.extend(conf.get("filter_packages"))
    catalog.include_filter.extend(conf.get("additional_packages"))

    # Create indexes
    package_index = {}
    repo_module_index = {}
    module_name_index = {}
    module_defaults = []

    # Add modules
    for repo in gpjson.keys():
        xml_path = f".//variant[@id='{repo}']/modules/module"
        modules = vxml.findall(xml_path)
        # No modules in repo, continue
        if len(modules) == 0:
            continue
        for module in modules:
            module_name = module.text.split(":")[0]
            if not repo in repo_module_index:
                repo_module_index[repo] = []
            repo_module_index[repo].append(module.text)
            module_name_index[module_name] = True
            print(f"Found module: {module.text}")

    # Add module defaults
    for mdtext in mdtexts:
        md = yaml.safe_load(mdtext)
        module_defaults.append(md)

    if len(module_defaults) > 0:
        catalog.module_defaults = module_defaults

    # Read prepopulate json and create package objects
    all_arches = []
    for repo in gpjson.keys():
        for arch in gpjson[repo].keys():
            if arch not in all_arches:
                all_arches.append(arch)
            for package in gpjson[repo][arch].keys():
                if package not in package_index:
                    package_index[package] = {}
                if repo not in package_index[package]:
                    package_index[package][repo] = {
                        "include_filter": [],
                        "multilib": [],
                    }
                na_list = gpjson[repo][arch][package]
                for na in na_list:
                    splitted = na.split(".")
                    arch_package = splitted[len(splitted) - 1]
                    if arch != arch_package and arch_package != "noarch":
                        if arch not in package_index[package][repo]["multilib"]:
                            package_index[package][repo]["multilib"].append(arch)
                    if na not in package_index[package][repo]["include_filter"]:
                        package_index[package][repo]["include_filter"].append(na)

    arch_specific_excludes = {}
    na_index = {}
    for pkg in package_index.keys():
        for repo in package_index[pkg].keys():
            na_list = list(
                filter(
                    lambda x: x.endswith(".noarch"),
                    package_index[pkg][repo]["include_filter"],
                )
            )
            if not na_list:
                continue
            exclude_arches = {}
            for na in na_list:
                for arch in all_arches:
                    if (
                        arch not in gpjson[repo]
                        or pkg not in gpjson[repo][arch]
                        or na not in gpjson[repo][arch][pkg]
                    ):
                        if na not in exclude_arches:
                            exclude_arches[na] = []
                        exclude_arches[na].append(arch)
                na_index[na] = na
            if not exclude_arches:
                continue
            if pkg not in arch_specific_excludes:
                arch_specific_excludes[pkg] = {}
            if repo not in arch_specific_excludes[pkg]:
                arch_specific_excludes[pkg][repo] = []
            arch_specific_excludes[pkg][repo].append(exclude_arches)

    # Index arch specific excludes by repo and arch
    repo_arch_index = {}
    for pkg in arch_specific_excludes.keys():
        for repo in arch_specific_excludes[pkg].keys():
            if repo not in repo_arch_index:
                repo_arch_index[repo] = {}
            for arches2 in arch_specific_excludes[pkg][repo]:
                for na in arches2.keys():
                    for arch in arches2[na]:
                        if arch not in repo_arch_index[repo]:
                            repo_arch_index[repo][arch] = []
                        if na not in repo_arch_index[repo][arch]:
                            repo_arch_index[repo][arch].append(na)

    # Add noarch packages not in a specific arch to exclude filter
    for repo in repo_arch_index.keys():
        repo_key = f"^{repo}$"
        filter_tuple = {}
        for arch in repo_arch_index[repo].keys():
            if arch not in filter_tuple:
                filter_tuple[arch] = []
            for na in repo_arch_index[repo][arch]:
                na = na.removesuffix(".noarch")
                if na not in filter_tuple[arch]:
                    filter_tuple[arch].append(na)
        catalog.exclude_filter.append((repo_key, filter_tuple))

    for package in package_index.keys():
        package_type = PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_FORK
        if package in module_name_index:
            package_type = PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_FORK_MODULE
        elif package.startswith("rocky-"):
            package_type = PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_SRC

        catalog.add_package(
            PeridotCatalogSyncPackage(
                package,
                package_type,
                [
                    PeridotCatalogSyncRepository(
                        x,
                        package_index[package][x]["include_filter"],
                        package_index[package][x]["multilib"],
                        (get_modules_for_repo(package, x, repo_module_index) if x in repo_module_index else None) if package in module_name_index else None,
                    )
                    for x in package_index[package].keys()
                ],
            )
        )

    print(f"Found {len(catalog.packages)} packages")

    f = open(output_path, "w")
    f.write(catalog.to_prototxt())
    f.close()

    print(f"Catalog written to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert Pungi configuration to Peridot compatible " "catalogs."
    )
    parser.add_argument("--pungi-conf-path", type=str, required=True)
    parser.add_argument("--major", type=int, required=True)
    parser.add_argument("--minor", type=int, required=True)
    parser.add_argument("--output-path", type=str, default="catalog.cfg")
    args = parser.parse_args()
    main(args.pungi_conf_path, args.output_path, args.major, args.minor)
