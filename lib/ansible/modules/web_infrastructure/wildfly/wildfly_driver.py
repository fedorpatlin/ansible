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
description:
- Installs jdbc-compliant database driver into working wildfly instance. Can install driver from deployment by deployment_name or from module. In that case a drivers module must be installed before run.
options:
    url:
        required: false
        default: http://localhost:9990/management
        description:
        - Management API url
    user:
        required: true
        description:
        - Management user
    password:
        required: true
        description:
        - Management user password
    driver_name:
        required: true
        description:
        - Driver name
    driver_module_name:
        required: true
        description:
        - Module name
    deployment_name
        required: false
        description:
        - name of deployment to load jdbc driver from
    driver_major_version:
        required: false
        description:
        - Driver major version
    driver_minor_version:
        required: false
        description:
        - Driver minor version number
    driver_class_name:
        required: false
        description:
        - Class name of jdbc driver. Can be determined automatically for JDBC-compliant drivers.
    driver_datasource_class_name:
        required: false
    driver_xa_datasource_class_name:
        required: false
    jdbc_compliant:
        required: false
    module_slot:
        required: false
        default: main
    profile:
        required: false
        description:
        - name of running profile. Only in domain mode.
    state:
        required: false
        default: present
        description:
        - If 'present' driver will be installed if not exists. If 'absent' driver will be removed if exists.
"""

EXAMPLES = """
- name: install driver from already installed module org.postgresql
  wildfly_driver:
    url: http://localhost:9990/management
    user: test
    password: testqa
    driver_name: postgres
    driver_module_name: org.postgresql
    state: present
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

    def __init__(self, **kwargs):
        self.name = kwargs.get('driver-name')
        self.module_name = ""
        self.test_api_path = ["subsystem", "datasources"]
        self.api_path = ["subsystem", "datasources", "jdbc-driver", self.name]
        self.test_method = 'installed-drivers-list'
        self.add_method = 'add'
        self.remove_method = 'remove'
        self.driver_args = kwargs

    def __add_to_dict_if_value(self, mydict, tuplekv):
        if tuplekv != None:
            mydict[tuplekv[0]] = tuplekv[1]
        return  mydict

    def get_driver_args(self, searchkey):
        "returns tuple (key, value) or None if key not found"
        if not isinstance(searchkey, str) or searchkey == "":
            return None
        if isinstance(self.driver_args, dict):
            value = self.driver_args.get(searchkey)
            if value is None:
                return None
        return (searchkey, value)

    def is_present(self, api):
        """Check driver with same name is already registered"""
        req = WildflyBasicRequest(self.test_api_path,
                                  self.test_method)
        driver_json = api.do_request(req)
        drivers_list = driver_json.get('result')
        if drivers_list != None:
            for driver in drivers_list:
                if driver.get('driver-name') == self.name:
                    return True
        return False

    def install(self, api):
        "Installs driver using module or deployment"
        args = dict()
        args = self.__add_to_dict_if_value(args, self.get_driver_args('driver-name'))
        args = self.__add_to_dict_if_value(args, self.get_driver_args('driver-module-name'))
        args = self.__add_to_dict_if_value(args, self.get_driver_args('deployment-name'))
        req = WildflyBasicRequest(
            self.api_path,
            self.add_method,
            **args)
        response = api.do_request(req)
        return response

    def remove(self, api):
        "remove driver by driver-name"
        req = WildflyBasicRequest(self.api_path, self.remove_method)
        response = api.do_request(req)
        return response

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
            driver_module_name=dict(required=False),
            deployment_name=dict(required=False),
            driver_major_version=dict(type=int),
            driver_minor_version=dict(type=int),
            driver_class_name=dict(required=False),
            driver_datasource_class_name=dict(required=False),
            driver_xa_datasource_class_name=dict(required=False),
            jdbc_compliant=dict(type=bool),
            module_slot=dict(default='main'),
            profile=dict(required=False),
            state=dict(default='present', choices=['present', 'absent'])
        ),
        supports_check_mode=True)
    url = module.params.get('url')
    user = module.params.get('user')
    password = module.params.get('password')
    required_state = module.params.get('state')
    driver_present = False
    driver_changed = False
    driver = WildflyDriver(
        **{
            'driver-name':module.params.get('driver_name'),
            'driver-module-name':module.params.get('driver_module_name'),
            'deployment-name':module.params.get('deployment_name'),
            'driver-major-version':module.params.get('driver_major_version'),
            'driver-minor-version':module.params.get('driver_minor_version'),
            'driver-class-name':module.params.get('driver_class_name'),
            'driver-datasource-class-name':module.params.get('driver_datasource_class_name'),
            'driver_xa_datasource_class_name':module.params.get('driver_xa_datasource_class_name'),
            'jdbc-compliant':module.params.get('jdbc_compliant'),
            'module-slot':module.params.get('module_slot'),
            'profile':module.params.get('profile'),
        }
        )

    api = WildflyApi(url, user, password)
    try:
        driver_present = driver.is_present(api)
    except Exception as ex:
        dump_error(module, ex)
    if required_state == 'present' and not driver_present:
        try:
            driver.install(api)
        except urllib2.HTTPError as err:
            dump_error(module, err)
        driver_changed = True
    if required_state == 'absent' and driver_present:
        try:
            driver.remove(api)
        except urllib2.HTTPError as err:
            dump_error(module, err)
        driver_changed = True
    module.exit_json(changed=driver_changed, msg="Success!")

if __name__ == '__main__':
    main()
