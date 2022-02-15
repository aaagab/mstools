#!/usr/bin/env python3
from datetime import datetime
from pprint import pprint
import json
import glob
from lxml import etree
import os
import re
import socket
import sys
import urllib.parse

from ..gpkgs.prompt import prompt_boolean
from ..gpkgs import message as msg

def get_profile(
    app_name,
    conf_apps,
    conf_profiles,
    direpa_root,
    filenpa_apps,
    filen_assembly,
    profile_name,
    profile_names,
):
    # <?xml version="1.0" encoding="utf-8"?>
    # <Project ToolsVersion="4.0" 
    #   xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
    #   <PropertyGroup>
    #   </PropertyGroup>
    # </Project>
    hostname=socket.gethostname().lower()

    if profile_name not in profile_names:
        print("Profile Unknown '{}' in '{}' > globals > confs".format(profile_name, filenpa_apps))
        sys.exit(1)

    direpa_publish_profiles=os.path.join(direpa_root, "Properties","PublishProfiles")

    if not os.path.exists(direpa_publish_profiles):
        msg.warning("Path not found '{}'".format(direpa_publish_profiles))
        if prompt_boolean("Do you want to create it") is True:
            os.makedirs(direpa_publish_profiles, exist_ok=True)
        else:
            msg.error("Path is needed for msbuild", exit=1)

    profiles=[]
    for elem in os.listdir(direpa_publish_profiles):
        filer, ext = os.path.splitext(elem)
        if ext == ".pubxml":
            profiles.append(filer)

    missing_confs=set(sorted(conf_profiles)) - set(profiles)
    if missing_confs:
        nsmap = { None: "http://schemas.microsoft.com/developer/msbuild/2003" }
        for missing_conf in missing_confs:
            filenpa_conf=os.path.join(direpa_publish_profiles, "{}.pubxml".format(missing_conf))
            node = etree.Element('Project', nsmap=nsmap)
            node.set("ToolsVersion", "4.0")
            child=etree.SubElement(node, "PropertyGroup")
            child.text=""
            etree.ElementTree(node).write(filenpa_conf, encoding='utf-8', xml_declaration=True, pretty_print=True)

    deploy_path=None
    if "deploy_path" in conf_profiles[profile_name]:
        if hostname in conf_profiles[profile_name]["deploy_path"]:
            if app_name not in conf_apps:
                msg.error("'{}' not found in conf '{}'".format(app_name, filenpa_apps))
                print("example:")
                print(json.dumps(dict(
                    apps={
                        "{}".format(app_name): dict(
                            port=9020,
                            direl="aa/{}".format(app_name)
                        )
                    },
                )))
                sys.exit(1)
            else:
                deploy_path=os.path.join(
                    conf_profiles[profile_name]["deploy_path"][hostname].replace("{user_profile}", os.path.expanduser("~")),
                    conf_apps[app_name]["direl"]
                ).replace("\\", "/")

    profile=dict(
        direpa_publish=os.path.normpath(os.path.join(direpa_root, "_publish", "build")),
        deploy_path=deploy_path,
        hostname_direl="",
        name=profile_name,
        web_config="",
    )

    if profile_name == "debug":
        profile["hostname_direl"]="{}:{}".format(
            conf_profiles[profile_name]["hostname"],
            conf_apps[app_name]["port"]
        )
    else:
        profile["hostname_direl"]="{}/{}".format(
            conf_profiles[profile_name]["hostname"],
            conf_apps[app_name]["direl"]
        )

    prefix=".{}".format(profile_name)
    if profile_name == "debug":
        prefix=""
    profile["web_config"]=os.path.join(direpa_root, "Web{}.config".format(prefix))

    filenpa_hostname=os.path.join(direpa_root, "hostname_url.txt")
    with open(filenpa_hostname, "w") as f:
        f.write("{}\n".format(profile["hostname_direl"]))
    profile["filenpa_cache_assembly"]=os.path.join(direpa_root, "obj", profile_name, filen_assembly)

    return profile
