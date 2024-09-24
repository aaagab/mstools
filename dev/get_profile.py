#!/usr/bin/env python3
from pprint import pprint
import json
from lxml import etree
import os
import sys

from .csproj import get_nsmap
from .get_settings import RawProfile, App, Profile

from ..gpkgs.prompt import prompt_boolean
from ..gpkgs import message as msg

def get_profile(
    app_name:str,
    apps:list[App],
    profiles:list[RawProfile],
    direpa_root:str,
    filenpa_settings:str,
    filen_assembly:str,
    profile_name:str,
    to_deploy:bool,
    direpa_deploy:str|None,
    no_pubxml:bool,
) :
    # <?xml version="1.0" encoding="utf-8"?>
    # <Project ToolsVersion="4.0" 
    #   xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
    #   <PropertyGroup>
    #   </PropertyGroup>
    # </Project>
    profile_names=[p.name for p in profiles]

    if to_deploy is True:
        if direpa_deploy is None:
            if profile_name not in profile_names:
                msg.error("Profile '{}' not found in  {}".format(profile_name, profile_names))
                print(f"In file '{filenpa_settings}' add a profile.")
                print("example:")
                print(json.dumps(dict(
                    profiles={
                        profile_name: {
                            "deploy_path(optional)": os.path.join(os.path.expanduser("~"), "fty", "local"),
                            "hostname": "https://localdomain.com"
                        }
                    },
                ), indent=4, sort_keys=True))
                sys.exit(1)

    p_index=profile_names.index(profile_name)
    raw_profile=profiles[p_index]

    app_names=[a.name for a in apps]
    if app_name not in app_names:
        msg.error("App '{}' not found in  {}".format(app_name, app_names))
        print(f"In file '{filenpa_settings}' add an app.")
        print("example:")
        print(json.dumps(dict(
            apps={
                app_name: {
                    "port": 9050,
                    "direl": "aa/info"
                }
            },
        ), indent=4, sort_keys=True))
        sys.exit(1)

    app_index=app_names.index(app_name)
    app=apps[app_index]

    if no_pubxml is False:
        direpa_publish_profiles=os.path.join(direpa_root, "Properties","PublishProfiles")

        if not os.path.exists(direpa_publish_profiles):
            msg.warning("Path not found '{}'".format(direpa_publish_profiles))
            if prompt_boolean("Do you want to create it") is True:
                os.makedirs(direpa_publish_profiles, exist_ok=True)
            else:
                msg.error("Path is needed for msbuild", exit=1)

        filenpa_profile=os.path.join(direpa_publish_profiles, "{}.pubxml".format(profile_name))
        if not os.path.exists(filenpa_profile):
            msg.warning("Not found '{}'".format(filenpa_profile))
            print()
            msg.warning("You may want to add the following line in your csproj:")
            print(r"""   
        <PropertyGroup Condition=" '$(Configuration)|$(Platform)' == '{}|AnyCPU' ">
            <DebugType>pdbonly</DebugType>
            <Optimize>true</Optimize>
            <OutputPath>bin</OutputPath>
            <DefineConstants>TRACE</DefineConstants>
            <ErrorReport>prompt</ErrorReport>
            <WarningLevel>4</WarningLevel>
        </PropertyGroup>
        <ItemGroup>
            <None Include="Properties\PublishProfiles\{}.pubxml"/>
        </ItemGroup>
                """.format(profile_name.capitalize(), profile_name))

            if prompt_boolean("Create file"):
                nsmap = { None: "http://schemas.microsoft.com/developer/msbuild/2003" }
                node = etree.Element('Project', nsmap=nsmap)#type:ignore
                node.set("ToolsVersion", "4.0")
                child=etree.SubElement(node, "PropertyGroup")
                child.text=""
                etree.ElementTree(node).write(filenpa_profile, encoding='utf-8', xml_declaration=True, pretty_print=True)
            else:
                msg.error("Action cancelled", exit=1)

    if to_deploy is True:
        if direpa_deploy is None:
            if raw_profile.direpa_deploy is None:
                print(raw_profile.to_json())
                msg.error(f"At '{filenpa_settings}' profile '{raw_profile.name}' deploy_path is needed.")
                sys.exit(1)
            direpa_deploy=os.path.normpath(os.path.join(raw_profile.direpa_deploy, app.direl))

    prefix=".{}".format(profile_name)
    if profile_name == "debug":
        prefix=""

    profile=Profile(
        direpa_deploy=direpa_deploy,
        direpa_publish=os.path.normpath(os.path.join(direpa_root, "_publish", "build")),
        filenpa_cache_assembly=os.path.join(direpa_root, "obj", profile_name, filen_assembly),
        hostname_direl=f"{raw_profile.hostname}/{app.direl}",
        name=profile_name,
        no_pubxml=no_pubxml,
        web_config=os.path.join(direpa_root, "Web{}.config".format(prefix)),
    )

    filenpa_hostname=os.path.join(direpa_root, "hostname_url.txt")
    with open(filenpa_hostname, "w") as f:
        f.write("{}\n".format(profile.hostname_direl))

    return profile
