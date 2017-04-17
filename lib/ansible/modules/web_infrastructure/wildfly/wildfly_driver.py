#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Module creates jdbc driver using wildfly's http api
"""
import json
import urllib2
import requests
from requests.auth import HTTPBasicAuth
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.basic import get_exception
from ansible.module_utils.urls import open_url

DOCUMENTATION = """
module: wildfly_driver
short_description: Add JDBC driver.
description: Installs jdbc-compliant database driver into working wildfly instance.
options:
    url:
        required: false
        description: management url
        default: http://localhost:9990/management
    user:
        required: true
        description: management user
    password:
        required: true
        description: management user password
"""

EXAMPLES = """
"""

class WildflyBasicRequest(object):
    "api request"
    def __init__(self, path, method, **method_params):
        self.path = path
        self.method = method
        self.method_params = method_params

    def __flatten_params(self, request):
        if len(self.method_params.keys()) < 1:
            return request
        for item in self.method_params.iteritems():
            keystring = item[0].replace('_', '-')
            request[keystring] = item[1]
        return request

    def to_json(self):
        """Does an generic request"""
        request = dict()
        request['address'] = self.path
        request['operation'] = self.method
        request = self.__flatten_params(request)
        return json.dumps(request)

class WildflyApi(object):
    """Api interaction"""
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.request_headers = {"Content-Type": "application/json", "Accept": "application/json"}

    def do_request(self, api_request):
        "send request to server"

        output = open_url(self.url,
                          data=api_request.to_json(),
                          method='POST',
                          url_username=self.user,
                          headers=self.request_headers,
                          url_password=self.password,
                          timeout=3)
        
        if output.getcode() == 200:
            response = output.read()
            driver_json = json.loads(response)
        return driver_json

class WildflyDriver(object):
    """Driver info needed for registration"""

    def __init__(self, driver_name, **kwargs):
        self.name = driver_name
        self.module_name = ""
        self.test_api_path = ["subsystem", "datasources"]
        self.api_path = ["subsystem", "datasources", "jdbc-driver", self.name]
        self.test_method = 'installed-drivers-list'
        self.add_method = 'add'
        self.remove_method = 'remove'
        self.deployment_name = kwargs.get('deployment_name')
        self.module_name = kwargs.get('module_name')
    def __add_to_dict_if_value(self, mydict, key, value):
        if value != None:
            mydict[key] = value
        return  mydict
    def is_present(self, api):
        """Check driver with same name is already registered"""
        req = WildflyBasicRequest(self.test_api_path,
                                  self.test_method)
        driver_json = api.do_request(req)
        if driver_json.get('outcome') == 'failed':
            raise IOError(driver_json.get('failure-description'))
        drivers_list = driver_json.get('result')
        if drivers_list != None:
            for driver in drivers_list:
                if driver.get('driver-name') == self.name:
                    return True
        return False

    def install(self, api):
        "Installs driver using module or deployment"
        args = dict()
        args = self.__add_to_dict_if_value(args, 'driver_name', self.name)
        args = self.__add_to_dict_if_value(args, 'driver_module_name', self.module_name)
        args = self.__add_to_dict_if_value(args, 'deployment_name', self.deployment_name)
        req = WildflyBasicRequest(
            self.api_path,
            self.add_method,
            **args)
        response = api.do_request(req)



def dump_error(module, ex):
    if isinstance(ex, urllib2.HTTPError):
        message = ex.read()
        obj = json.loads(message)
        result = obj.get('failure-description')
        module.fail_json(msg=json.dumps(result))
    else:
        module.fail_json(msg=json.dumps(ex.message))


def main():
    """Module init"""
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(default='http://localhost:9990/management'),
            user=dict(required=True),
            password=dict(required=True, no_log=True),
            driver_name=dict(required=True),
            module_name=dict(required=False),
            deployment_name=dict(required=False),
            state=dict(default='present', choices=['present', 'absent'])
        ),
        supports_check_mode=True)
    url = module.params.get('url')
    user = module.params.get('user')
    password = module.params.get('password')
    driver_name = module.params.get('driver_name')
    module_name = module.params.get('module_name')
    deployment_name = module.params.get('deployment_name')
    driver_present = False
    driver_changed = False
    driver = WildflyDriver(driver_name, module_name=module_name, deployment_name=deployment_name)

    api = WildflyApi(url, user, password)
    try:
        driver_present = driver.is_present(api)
    except Exception as ex:
        dump_error(module, ex)
    if not driver_present:
        try:
            driver.install(api)
        except urllib2.HTTPError as err:
            dump_error(module, err)
        driver_changed = True
    module.exit_json(changed=driver_changed, msg="Success!")

if __name__ == '__main__':
    main()
