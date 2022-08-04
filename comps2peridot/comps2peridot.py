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

# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from xml.dom import minidom

from group import Group, PackageReq, Environment, EnvGroup


def write_variant(groups, environments, categories, out):
    root = ET.Element("comps")
    for group in groups:
        group_elem = ET.SubElement(root, "group")
        ET.SubElement(group_elem, "id").text = group.id
        for lang in group.name:
            name = ET.SubElement(group_elem, "name")
            if lang != "":
                name.set("xml:lang", lang)
            name.text = group.name[lang]
        for lang in group.description:
            description = ET.SubElement(group_elem, "description")
            if lang != "":
                description.set("xml:lang", lang)
            description.text = group.description[lang]
        ET.SubElement(group_elem, "default").text = str(group.default).lower()
        ET.SubElement(group_elem, "uservisible").text = str(group.user_visible).lower()
        package_list = ET.SubElement(group_elem, "packagelist")
        for package in group.packages:
            package_elem = ET.SubElement(package_list, "packagereq")
            package_elem.set("type", package.type)
            package_elem.text = package.name
    for environment in environments:
        env_elem = ET.SubElement(root, "environment")
        ET.SubElement(env_elem, "id").text = environment.id
        for lang in environment.name:
            name = ET.SubElement(env_elem, "name")
            if lang != "":
                name.set("xml:lang", lang)
            name.text = environment.name[lang]
        for lang in environment.description:
            description = ET.SubElement(env_elem, "description")
            if lang != "":
                description.set("xml:lang", lang)
            description.text = environment.description[lang]
        ET.SubElement(env_elem, "display_order").text = str(environment.display_order)
        group_list = ET.SubElement(env_elem, "grouplist")
        for group in environment.group_list:
            ET.SubElement(group_list, "groupid").text = group.name
        option_list = ET.SubElement(env_elem, "optionlist")
        for option in environment.option_list:
            ET.SubElement(option_list, "optionid").text = option.name
    for category_name in categories.keys():
        category = categories[category_name]
        new_group_list = []
        for group in category.group_list:
            for ggroup in groups:
                if ggroup.id == group.name:
                    new_group_list.append(group)
                    break
        if len(new_group_list) == 0:
            continue
        category_elem = ET.SubElement(root, "category")
        ET.SubElement(category_elem, "id").text = category_name
        for lang in category.name:
            name = ET.SubElement(category_elem, "name")
            if lang != "":
                name.set("xml:lang", lang)
            name.text = category.name[lang]
        for lang in category.description:
            description = ET.SubElement(category_elem, "description")
            if lang != "":
                description.set("xml:lang", lang)
            description.text = category.description[lang]
        ET.SubElement(category_elem, "display_order").text = str(category.display_order)
        group_list = ET.SubElement(category_elem, "grouplist")
        for group in new_group_list:
            ET.SubElement(group_list, "groupid").text = group.name
    ET.ElementTree(root).write(out, encoding="utf-8", xml_declaration=False)

    with open(out, "r") as f:
        data = f.read()
    with open(out, "w") as f:
        f.writelines(
            """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE comps
  PUBLIC '-//Red Hat, Inc.//DTD Comps info//EN'
  'comps.dtd'>
"""
            + minidom.parseString(data)
            .toprettyxml(indent="  ")
            .replace('<?xml version="1.0" ?>\n', "")
        )


def main(comps_path: str, variants_path: str, output_path: str):
    default_arches = ["x86_64", "aarch64", "ppc64le", "s390x"]
    variants = {}
    environments = {}
    categories = {}

    tree = ET.parse(comps_path)
    root = tree.getroot()
    for gchild in root:
        if gchild.tag == "group":
            group_name = {}
            group_desc = {}
            group_id = ""
            is_default = False
            is_visible = False
            variant = ""
            package_list_xml = None
            if "variant" in gchild.attrib:
                variant = gchild.attrib["variant"]
            if "arch" in gchild.attrib:
                arches = gchild.attrib["arch"].split(",")
            else:
                arches = default_arches
            for gattr in gchild:
                if gattr.tag == "id":
                    group_id = gattr.text
                elif gattr.tag == "name":
                    if "{http://www.w3.org/XML/1998/namespace}lang" in gattr.attrib:
                        group_name[
                            gattr.attrib["{http://www.w3.org/XML/1998/namespace}lang"]
                        ] = gattr.text
                    else:
                        group_name[""] = gattr.text
                elif gattr.tag == "description":
                    if "{http://www.w3.org/XML/1998/namespace}lang" in gattr.attrib:
                        group_desc[
                            gattr.attrib["{http://www.w3.org/XML/1998/namespace}lang"]
                        ] = gattr.text
                    else:
                        group_desc[""] = gattr.text
                elif gattr.tag == "default":
                    is_default = gattr.text == "true"
                elif gattr.tag == "uservisible":
                    is_visible = gattr.text == "true"
                elif gattr.tag == "packagelist":
                    package_list_xml = gattr
            package_list = {}
            if variant != "":
                package_list[variant] = {}
            for reqxml in package_list_xml:
                req_variant = variant
                req_type = "default"
                if "variant" in reqxml.attrib:
                    req_variant = reqxml.attrib["variant"]
                if "type" in reqxml.attrib:
                    req_type = reqxml.attrib["type"]
                if "arch" in reqxml.attrib:
                    req_arches = reqxml.attrib["arch"].split(",")
                else:
                    req_arches = arches
                if req_variant not in package_list:
                    package_list[req_variant] = {}
                for arch in req_arches:
                    if arch not in package_list[req_variant]:
                        package_list[req_variant][arch] = []
                    package_list[req_variant][arch].append(
                        PackageReq(reqxml.text, req_type, req_arches)
                    )
            for variant in package_list:
                if variant not in variants:
                    variants[variant] = {}
                for arch in arches:
                    if arch not in package_list[variant]:
                        package_list[variant][arch] = []
                    if group_id not in variants[variant]:
                        variants[variant][group_id] = {}
                    variants[variant][group_id][arch] = Group(
                        group_id,
                        group_name,
                        group_desc,
                        is_default,
                        is_visible,
                        package_list[variant][arch],
                    )
        elif gchild.tag == "environment" or gchild.tag == "category":
            env_name = {}
            env_desc = {}
            env_id = ""
            display_order = 0
            group_list = []
            option_list = []
            for gattr in gchild:
                if gattr.tag == "id":
                    env_id = gattr.text
                elif gattr.tag == "name":
                    if "{http://www.w3.org/XML/1998/namespace}lang" in gattr.attrib:
                        env_name[
                            gattr.attrib["{http://www.w3.org/XML/1998/namespace}lang"]
                        ] = gattr.text
                    else:
                        env_name[""] = gattr.text
                elif gattr.tag == "description":
                    if "{http://www.w3.org/XML/1998/namespace}lang" in gattr.attrib:
                        env_desc[
                            gattr.attrib["{http://www.w3.org/XML/1998/namespace}lang"]
                        ] = gattr.text
                    else:
                        env_desc[""] = gattr.text
                elif gattr.tag == "display_order":
                    display_order = gattr.text
                elif gattr.tag == "grouplist":
                    for group in gattr:
                        if "arch" in group.attrib:
                            arches = group.attrib["arch"].split(",")
                        else:
                            arches = default_arches
                        group_list.append(EnvGroup(group.text, arches))
                elif gattr.tag == "optionlist":
                    for group in gattr:
                        if "arch" in group.attrib:
                            arches = group.attrib["arch"].split(",")
                        else:
                            arches = default_arches
                        option_list.append(EnvGroup(group.text, arches))
            new_env = Environment(
                env_id, env_name, env_desc, display_order, group_list, option_list
            )
            dictmap = categories
            if gchild.tag == "environment":
                dictmap = environments
            if "arch" in gchild.attrib:
                arches = gchild.attrib["arch"].split(",")
            else:
                arches = default_arches
            for arch in arches:
                if arch not in dictmap:
                    dictmap[arch] = {}
                dictmap[arch][env_id] = new_env

    environment_id_index = {}
    for arch in environments.keys():
        for env in environments[arch].values():
            if env.id not in environment_id_index:
                environment_id_index[env.id] = {}
            environment_id_index[env.id][arch] = env

    variant_arch_index = {}
    environment_arch_index = {}
    pungi_variants_tree = ET.parse(variants_path).getroot()
    for pungi_variant in pungi_variants_tree:
        if pungi_variant.tag == "variant":
            if pungi_variant.attrib["type"] != "variant":
                continue
            arches = []
            groups = {}
            n_environments = {}
            variant_id = pungi_variant.attrib["id"]
            for child in pungi_variant:
                if child.tag == "arches":
                    for arch in child:
                        arches.append(arch.text)
                elif child.tag == "groups":
                    for group in child:
                        groupbase = variants[""]
                        if variant_id in variants:
                            groupbase = variants[variant_id]
                        if group.text not in groupbase:
                            continue
                        groupind = groupbase[group.text].copy()
                        for arch_group in groupind.keys():
                            if arch_group not in groups:
                                groups[arch_group] = []
                            if "default" in group.attrib:
                                groupind[arch_group].default = (
                                    group.attrib["default"] == "true"
                                )
                            groups[arch_group].append(groupind[arch_group])
                elif child.tag == "environments":
                    for environment in child:
                        envind = environment_id_index[environment.text]
                        for arch_environment in envind.keys():
                            if arch_environment not in n_environments:
                                n_environments[arch_environment] = []
                            n_environments[arch_environment].append(
                                envind[arch_environment]
                            )
            for arch in arches:
                if arch in groups:
                    if arch not in variant_arch_index:
                        variant_arch_index[arch] = {}
                    if variant_id not in variant_arch_index[arch]:
                        variant_arch_index[arch][variant_id] = []
                    variant_arch_index[arch][variant_id].extend(groups[arch])
                if arch in n_environments:
                    if arch not in environment_arch_index:
                        environment_arch_index[arch] = {}
                    if variant_id not in environment_arch_index[arch]:
                        environment_arch_index[arch][variant_id] = []
                    environment_arch_index[arch][variant_id].extend(
                        n_environments[arch]
                    )

    for arch in variant_arch_index.keys():
        for variant in variant_arch_index[arch].keys():
            write_variant(
                variant_arch_index[arch][variant]
                if variant in variant_arch_index[arch]
                else [],
                environment_arch_index[arch][variant]
                if variant in environment_arch_index[arch]
                else [],
                categories[arch].copy(),
                f"{output_path}/{variant}-{arch}.xml",
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert comps to Peridot compatible configuration."
    )
    parser.add_argument("--comps-path", type=str, required=True)
    parser.add_argument("--variants-path", type=str, required=True)
    parser.add_argument("--output-path", type=str, default=".")
    args = parser.parse_args()
    main(args.comps_path, args.variants_path, args.output_path)
