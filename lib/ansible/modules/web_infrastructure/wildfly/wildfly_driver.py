#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Module creates jdbc driver using wildfly's http api
"""
import json
import requests
from requests.auth import HTTPBasicAuth
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.basic import get_exception
from ansible.module_utils.urls import open_url

DOCUMENTATION = """
url - management url
user - management user
password - management user password
"""

EXAMPLES = """
"""

def main():
    """Module init"""
    module = AnsibleModule(argument_spec=dict(
        url=dict(default='http://localhost:9990/management'),
        user=dict(required=True),
        password=dict(required=True, no_log=True),
    ))
    url = module.params.get('url')
    user = module.params.get('user')
    password = module.params.get('password')
    try:
        open_url(url, url_username=user, url_password=password, timeout=3)
    except Exception:
        ex = get_exception()
        module.fail_json(msg="{}".format(type(ex)))
    module.exit_json(changed=False)

if __name__ == '__main__':
    main()
