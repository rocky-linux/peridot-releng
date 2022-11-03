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

import xml.etree.ElementTree as ET
import json
import os
import tempfile

from git import Repo

class SCM:
    def __init__(self, pungi_base, scm_dict, ext_filters=None):
        # Temporary hack since pungi-rocky usually has everything in one repo anyways
        # todo(mustafa): remove this hack
        base_file_path = ""
        base_file_dir = ""
        if isinstance(scm_dict, str):
            base_file_path = scm_dict
        else:
            if scm_dict["scm"] == "file":
                base_file_path = scm_dict["file"]
            elif scm_dict["scm"] == "git":
                if "file" in scm_dict:
                    base_file_path = scm_dict["file"]
                elif "dir" in scm_dict:
                    base_file_dir = scm_dict["dir"]
            else:
                raise Exception("Unsupported SCM type")

        file_contents = None
        file_list_contents = []

        if  isinstance(scm_dict, str) or scm_dict["scm"] == "file":
            file_path = os.path.join(pungi_base, base_file_path)

            f = open(file_path, "r")
            file_contents = f.read()
            f.close()
        elif scm_dict["scm"] == "git":
            with tempfile.TemporaryDirectory() as d:
                print(f"Cloning {scm_dict['repo']}")
                Repo.clone_from(scm_dict["repo"], d, branch=scm_dict["branch"], depth=1)

                if base_file_path:
                    print(f"Found file {base_file_path}")
                    file_path = os.path.join(d, base_file_path)
                    f = open(file_path, "r")
                    file_contents = f.read()
                    f.close()
                elif base_file_dir:
                    print(f"Reading files from {base_file_dir}")
                    file_dir = os.path.join(d, base_file_dir)
                    for file in os.listdir(file_dir):
                        if file in [".git"]:
                            continue
                        if ext_filters:
                            if not any(file.endswith(ext) for ext in ext_filters):
                                continue
                        file_path = os.path.join(file_dir, file)
                        f = open(file_path, "r")
                        file_list_contents.append(f.read())
                        f.close()

        if file_contents:
            if base_file_path.endswith(".json"):
                self.json_value = json.loads(file_contents)
            elif base_file_path.endswith(".xml"):
                self.xml_value = ET.fromstring(file_contents)
            else:
                self.text_value = file_contents
        elif file_list_contents:
            self.text_values = file_list_contents

    def json(self):
        return self.json_value

    def text(self):
        return self.text_value

    def xml(self):
        return self.xml_value

    def texts(self):
        return self.text_values
