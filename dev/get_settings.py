#!/usr/bin/env python3
from pprint import pprint
import os
import json
import sys

from ..gpkgs import message as msg

class Profile():
    def __init__(self,
        direpa_deploy:str|None,
        direpa_publish:str,
        filenpa_cache_assembly:str,
        hostname_direl:str,
        name:str,
        no_pubxml:bool,
        web_config:str,
    ):
        self.direpa_deploy=direpa_deploy
        self.direpa_publish=direpa_publish
        self.filenpa_cache_assembly=filenpa_cache_assembly
        self.hostname_direl=hostname_direl
        self.name=name
        self.no_pubxml=no_pubxml
        self.web_config=web_config
        
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4, sort_keys=True)

class App():
    def __init__(self,
        name:str,
        port:int,
        direl:str,
    ):
        self.name=name
        self.port=port
        self.direl=direl

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class RawProfile():
    def __init__(self,
        name:str,
        direpa_deploy:str|None,
        hostname:str,
        # direpa_pub
    ):
        self.name=name
        self.direpa_deploy=direpa_deploy
        self.hostname=hostname

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4, sort_keys=True)

class Settings():
    def __init__(self,
        apps:list[App],
        profiles:list[RawProfile],
        direpa_framework:str,
        filenpa_express:str,
        filenpa_csc:str,
        filenpa_msbuild:str,
        filenpa_msdeploy:str,
    ):
        self.apps=apps
        self.profiles=profiles
        self.direpa_framework=direpa_framework
        self.filenpa_express=filenpa_express
        self.filenpa_csc=filenpa_csc
        self.filenpa_msbuild=filenpa_msbuild
        self.filenpa_msdeploy=filenpa_msdeploy

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4, sort_keys=True)

def get_settings(
    filenpa_settings:str,
) -> Settings:
    if not os.path.exists(filenpa_settings):
        msg.error("Not found '{}'".format(filenpa_settings), exit=1)

    dy_conf:dict
    with open(filenpa_settings, "r") as f:
        dy_conf=json.load(f)

    if "apps" not in dy_conf:
        raise Exception(f"In file '{filenpa_settings}' key 'apps' missing")
    
    dy_apps=dy_conf["apps"]
    if isinstance(dy_apps, dict) is False:
        raise Exception(f"In file '{filenpa_settings}' key 'apps' type must be {dict}")
    
    apps:list[App]=[]
    for app_name, app_conf in sorted(dy_conf["apps"].items()):
        if isinstance(app_name, str) is False:
            raise Exception(f"In file '{filenpa_settings}' in 'apps' key '{app_name}' type must be {str}")
        
        port:int
        direl:str
        name:str=app_name

        if isinstance(app_conf, dict) is False:
            raise Exception(f"In file '{filenpa_settings}' in 'apps' key '{app_name}' value '{app_conf}' type must be {dict}")
        
        if "port" in app_conf and isinstance(app_conf["port"], int):
            port=app_conf["port"]
        else:
            raise Exception(f"In file '{filenpa_settings}' in 'apps' name '{app_name}' required key 'port' type must be {str} and its value must be type {int}")

        if "direl" in app_conf and isinstance(app_conf["direl"], str):
            direl=app_conf["direl"]
        else:
            raise Exception(f"In file '{filenpa_settings}' in 'apps' name '{app_name}' required key 'direl' type must be {str} and its value must be type {str}")
        
        apps.append(App(name=name, direl=direl, port=port))

    dy_profiles=dy_conf["profiles"]
    if isinstance(dy_profiles, dict) is False:
        raise Exception(f"In file '{filenpa_settings}' key 'profiles' type must be {dict}")
    
    profiles:list[RawProfile]=[]
    for profile_name, profile_conf in sorted(dy_conf["profiles"].items()):
        if isinstance(profile_name, str) is False:
            raise Exception(f"In file '{filenpa_settings}' in 'profiles' key '{profile_name}' type must be {str}")
        
        if isinstance(profile_conf, dict) is False:
            raise Exception(f"In file '{filenpa_settings}' in 'profiles' key '{app_name}' value '{profile_conf}' type must be {dict}")
        
        direpa_deploy:str|None=None
        hostname:str

        if "hostname" in profile_conf and isinstance(profile_conf["hostname"], str):
            hostname=profile_conf["hostname"]
        else:
            raise Exception(f"In file '{filenpa_settings}' in 'profiles' name '{app_name}' required key 'hostname' type must be {str} and its value must be type {str}")

        if "deploy_path" in profile_conf:
            if isinstance(profile_conf["deploy_path"], str):
                direpa_deploy=os.path.normpath(profile_conf["deploy_path"].format(user_profile=os.path.expanduser("~")))
            else:
                raise Exception(f"In file '{filenpa_settings}' in 'profiles' name '{app_name}' key 'deploy_path' type must be {str} and its value must be type {str}")
        
        profiles.append(RawProfile(name=profile_name, direpa_deploy=direpa_deploy, hostname=hostname))

    direpa_framework:str
    if "direpa_framework" in dy_conf and isinstance(dy_conf["direpa_framework"], str):
        direpa_framework=os.path.normpath(dy_conf["direpa_framework"])
    else:
        raise Exception(f"In file '{filenpa_settings}' required key 'direpa_framework' type must be {str} and its value must be type {str}")

    filenpa_express:str
    if "filenpa_express" in dy_conf and isinstance(dy_conf["filenpa_express"], str):
        filenpa_express=os.path.normpath(dy_conf["filenpa_express"])
    else:
        raise Exception(f"In file '{filenpa_settings}' required key 'filenpa_express' type must be {str} and its value must be type {str}")

    filenpa_csc:str
    if "filenpa_csc" in dy_conf and isinstance(dy_conf["filenpa_csc"], str):
        filenpa_csc=os.path.normpath(dy_conf["filenpa_csc"])
    else:
        raise Exception(f"In file '{filenpa_settings}' required key 'filenpa_csc' type must be {str} and its value must be type {str}")
    
    filenpa_msbuild:str
    if "filenpa_msbuild" in dy_conf and isinstance(dy_conf["filenpa_msbuild"], str):
        filenpa_msbuild=os.path.normpath(dy_conf["filenpa_msbuild"])
    else:
        raise Exception(f"In file '{filenpa_settings}' required key 'filenpa_msbuild' type must be {str} and its value must be type {str}")

    filenpa_msdeploy:str
    if "filenpa_msdeploy" in dy_conf and isinstance(dy_conf["filenpa_msdeploy"], str):
        filenpa_msdeploy=os.path.normpath(dy_conf["filenpa_msdeploy"])
    else:
        raise Exception(f"In file '{filenpa_settings}' required key 'filenpa_msdeploy' type must be {str} and its value must be type {str}")

    settings=Settings(
        apps=apps,
        profiles=profiles,
        direpa_framework=direpa_framework,
        filenpa_express=filenpa_express,
        filenpa_csc=filenpa_csc,
        filenpa_msbuild=filenpa_msbuild,
        filenpa_msdeploy=filenpa_msdeploy,
    )

    return settings
