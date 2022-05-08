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

import kobo.conf

from catalog import PeridotCatalogSync, PeridotCatalogSyncPackage, \
    PeridotCatalogSyncPackageType, PeridotCatalogSyncRepository
from scm import SCM


def main(pungi_conf_path: str, output_path: str):
    pungi_base = os.path.dirname(pungi_conf_path)

    conf = kobo.conf.PyConfigParser()
    conf.load_from_file(pungi_conf_path)

    gather_prepopulate_scm_dict = conf.get("gather_prepopulate")
    gpscm = SCM(pungi_base, gather_prepopulate_scm_dict)
    gpjson = gpscm.json()

    # Create a catalog
    catalog = PeridotCatalogSync()

    # Set multilib filters
    catalog.additional_multilib.extend(
        list(conf.get("multilib_whitelist").values())[0])
    catalog.exclude_multilib_filter.extend(
        list(conf.get("multilib_blacklist").values())[0])

    # Set additional packages/filters
    catalog.exclude_filter.extend(conf.get("filter_packages"))
    catalog.include_filter.extend(conf.get("additional_packages"))

    # Create indexes
    package_index = {}

    # Read prepopulate json and create package objects
    for repo in gpjson.keys():
        for arch in gpjson[repo].keys():
            for package in gpjson[repo][arch].keys():
                if package not in package_index:
                    package_index[package] = {}
                if repo not in package_index[package]:
                    package_index[package][repo] = {"include_filter": [],
                                                    "multilib": []}
                na_list = gpjson[repo][arch][package]
                for na in na_list:
                    splitted = na.split(".")
                    arch_package = splitted[len(splitted) - 1]
                    if arch != arch_package and arch_package != "noarch":
                        if arch not in package_index[package][repo]["multilib"]:
                            package_index[package][repo]["multilib"].append(
                                arch)
                    if na not in package_index[package][repo]["include_filter"]:
                        package_index[package][repo]["include_filter"].append(
                            na)

    for package in package_index.keys():
        catalog.add_package(
            PeridotCatalogSyncPackage(
                package,
                PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_FORK if not package.startswith("rocky-") else PeridotCatalogSyncPackageType.PACKAGE_TYPE_NORMAL_SRC,
                [],
                [PeridotCatalogSyncRepository(x, package_index[package][x][
                    "include_filter"], package_index[package][x]["multilib"])
                 for
                 x in package_index[package].keys()]
            )
        )

    f = open(output_path, "w")
    f.write(catalog.to_prototxt())
    f.close()

    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert Pungi configuration to Peridot compatible '
                    'catalogs.')
    parser.add_argument('--pungi-conf-path', type=str, required=True)
    parser.add_argument('--output-path', type=str, default="catalog.cfg")
    args = parser.parse_args()
    main(args.pungi_conf_path, args.output_path)
