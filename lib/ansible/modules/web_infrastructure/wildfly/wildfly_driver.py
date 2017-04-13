#!/bin/env python
# -*- coding: UTF-8 -*-
import json
import requests
from requests.auth import HTTPBasicAuth
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION="""
"""

EXAMPLES="""
"""

def main():
    """Module init"""
    module = AnsibleModule(argument_spec=dict(
        port=dict(default=9990)
    ))
    module.exit_json(changed=False)

if __name__ == '__main__':
    main()