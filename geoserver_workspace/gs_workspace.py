#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json
import requests
from requests.auth import HTTPBasicAuth
from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = """
---
module = gs_workspace
short_description: Creates geoserver (geoserver.org) workspace using rest api.
Requires requests library to be installed on target host.
"""
EXAMPLES = """
gs_workspace host='localhost' port='8080' user='admin' password='geoserver' name='myworkspace' default='yes' state='present'

Creates workspace with name 'myworkspace' ands point default workspace to it.

"""

class GsWorkspace(object):
    """
    class to hold all global variables
    """
    def __init__(self, name, is_default_workspace, uri, session, state):
        self.name = name
        self.default = is_default_workspace
        self.uri = uri
        self.session = session
        self.raw_data = ''
        self.state = state
        self.is_exists = False
        self.changed = False
        if self.state == 'present':
            self.__fetch()
        elif self.state == 'absent':
            self.__delete()

    def __fetch(self):
        """getting workspace or 404"""
        resp = self.session.get(u'{}/{}.json?quietOnNotFound=true'.format(self.uri, self.name))
        if resp.status_code == 200:
            self.raw_data = json.loads(resp.content)
            self.is_exists = True
            self.__set_default()
        elif resp.status_code == 404 and self.state == u'present':
            self.__create()

    def __create(self):
        data = json.dumps({'workspace':{'name': self.name}})
        response = self.session.post(u'{}.json'.format(self.uri), data)
        if response.status_code == 201:
            self.is_exists = True
            self.changed = True
            self.__fetch()

    def __fetch_default(self):
        resp = self.session.get(u'{}/default'.format(self.uri))
        if resp.status_code == 200:
            default_workspace = json.loads(resp.content)
            if isinstance(default_workspace, dict):
                return default_workspace.get('workspace').get('name')

    def __is_default(self):
        return self.name == self.__fetch_default()

    def __set_default(self):
        if self.default and not self.__is_default():
            data = json.dumps({'workspace':{'name':self.name}})
            response = self.session.put(u'{}/default'.format(self.uri), data)
            if response.status_code == 200:
                self.changed = True
                self.default = True

    def __delete(self):
        resp = self.session.delete(u'{}/{}.json?quietOnNotFound=true'.format(self.uri, self.name))
        if resp.status_code == 200:
            self.changed = True
            self.is_exists = False
        elif resp.status_code == 404:
            self.changed = False
            self.is_exists = False



# ===========================================
# Module execution.
#
def main():
    """Module initialization"""
    module = AnsibleModule(
        argument_spec=dict(
            secure=dict(default=True, type='bool'),
            host=dict(default='localhost'),
            port=dict(default='8080'),
            user=dict(default='admin'),
            path=dict(default='/geoserver'),
            password=dict(default='geoserver', no_log=True),
            state=dict(default='present', choices=['present', 'absent']),
            name=dict(required=True),
            default=dict(default=False, type='bool'),
        )
    )
    # setup parameters
    secure = module.params.get('secure')
    host = module.params.get('host')
    port = module.params.get('port')
    user = module.params.get('user')
    path = module.params.get('path')
    password = module.params.get('password')
    state = module.params.get('state')
    ws_name = module.params['name']
    is_default = module.params.get('default')
    if secure is True:
        api_url_proto = 'https'
    else:
        api_url_proto = 'http'
    api_url_template = u'{0}://{1}:{2}{3}/rest/workspaces'
    workspace_api_url = api_url_template.format(api_url_proto, host, port, path)
    #configure basic authentication
    basic_auth = HTTPBasicAuth(user, password)
    session = requests.Session()
    session.auth = basic_auth
    session.headers['Content-Type'] = u'text/json'
    session.headers['Accept'] = u'text/json'

    workspace = GsWorkspace(ws_name, is_default, workspace_api_url, session, state)
    if state == 'present':
        if workspace.is_exists:
            session.close()
            module.exit_json(changed=workspace.changed, default=workspace.default)
        else:
            session.close()
            module.fail_json(msg="error creating workspace")
    elif state == 'absent':
        if not workspace.is_exists:
            session.close()
            module.exit_json(changed=workspace.changed)
        else:
            session.close()
            module.fail_json(msg="error deleting workspace")
    else:
        module.fail_json(msg="WTF")
if __name__ == '__main__':
    main()
