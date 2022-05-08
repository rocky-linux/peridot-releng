#!/usr/bin/env python3

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

import sys
import requests
import json


def get_batch(batch_type, task_id, status, page):
    r = requests.get(
        f'https://peridot.pdot-dev.rockylinux.org/api/v1/projects/c4fa14a2-5af6-4634-bfea-847a9fd639c7/{batch_type}_batches/{task_id}?page={page}&limit=100&filter.status={status}')
    return r.json()[f'{batch_type}s']


def process_batch(batch_type, task_id, status):
    ret = []
    page = 0
    while True:
        res = get_batch(batch_type, task_id, status, page)
        if len(res) == 0:
            return ret
        ret.extend(res)
        page = page + 1


if __name__ == '__main__':
    batch_type = sys.argv[1]
    task_id = sys.argv[2]

    batch_items = process_batch(batch_type, task_id, 4)
    # batch_items.extend(process_batch(batch_type, task_id, 5))

    req = {}
    key = f'{batch_type}s'
    req[key] = []
    for item in batch_items:
        req[key].append({
            'package_name': item['name']
        })

    print(json.dumps(req))
