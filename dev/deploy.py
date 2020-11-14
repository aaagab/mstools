#!/usr/bin/env python3
import json
from lxml import etree
from pprint import pprint
import os
import re
import subprocess
import shutil
import sys
import tempfile

from ..gpkgs import message as msg
from ..gpkgs import shell_helpers as shell

def deploy(
    filenpa_msdeploy,
    deploy_path,
    direpa_publish,
    push_paths,
):


    cmd=[]
    filenpa_tmp=None
    success=False
    if deploy_path[:6] == "ftp://":
        winscp_profile=deploy_path[6:].split("/")[0]
        direpa_ftp_dst=deploy_path[6+len(winscp_profile):].replace("\\", "/")
        deploy_paths=get_paths(direpa_ftp_dst, direpa_publish, push_paths)

        direpa_not_found=(winscp_cmd(winscp_profile, "stat {}".format(direpa_ftp_dst), fail=False) == 1)
        if direpa_not_found:
            msg.error("ftp path not found '{}'".format(direpa_ftp_dst), exit=1)

        if deploy_paths is None:
            cmd=r'synchronize remote -mirror -delete -criteria=time -transfer=automatic -filemask="| */App_Data/log.txt; */Uploads/; */Logs/" "{}" "{}"'.format(
                direpa_publish,
                direpa_ftp_dst,
            )
            winscp_cmd(winscp_profile, cmd)
        else:
            for dy_path in deploy_paths:
                direpa_not_found=(winscp_cmd(winscp_profile, "stat {}".format(dy_path["direpa_dst"]), fail=False) == 1)
                if direpa_not_found:
                    winscp_cmd(winscp_profile, "mkdir \"{}\"".format(dy_path["direpa_dst"]))
                if dy_path["type"] == "file":
                    cmd="put \"{}\" \"{}\"".format(
                        dy_path["src"].replace("/", "\\"),
                        os.path.dirname(dy_path["dst"])+"/",
                    )
                    winscp_cmd(winscp_profile, cmd)
                elif dy_path["type"] == "dir":
                    direpa_not_found=(winscp_cmd(winscp_profile, "stat {}".format(dy_path["dst"]), fail=False) == 1)
                    if direpa_not_found:
                        winscp_cmd(winscp_profile, "mkdir \"{}\"".format(dy_path["dst"]))
                    cmd=r'synchronize remote -mirror -delete -criteria=time -transfer=automatic -filemask="| */App_Data/log.txt; */Uploads/; */Logs/" "{}" "{}"'.format(
                        dy_path["src"],
                        dy_path["dst"],
                    )
                    winscp_cmd(winscp_profile, cmd)
    else:
        deploy_path=os.path.normpath(deploy_path)
        deploy_paths=get_paths(deploy_path, direpa_publish, push_paths)

        if deploy_paths is None:
            # msdeploy is needed because msbuild can't preserve an Uploads folder when updating and removing all the rest.
            cmd=[
                filenpa_msdeploy,
                "-verb:sync",
                r"-source:dirPath={}".format(direpa_publish),
                r"-dest:dirPath={}".format(deploy_path),
                r"-skip:objectName=dirPath,absolutePath={}\.*".format(os.path.join(deploy_path, "Uploads").replace("\\", "\\\\")),
                r"-skip:objectName=dirPath,absolutePath={}\.*".format(os.path.join(deploy_path, "Logs").replace("\\", "\\\\")),
                r"-skip:objectName=filePath,absolutePath=App_Data\\log.txt",
                # # r"-setParamFile:{}",
                # -skip:attribute1=value1[,attribute2=value2[.. ,attributeN=valueN]]
            ]
        
            shell.cmd_prompt(cmd)
        else:
            for dy_path in deploy_paths:
                dy_path["src"]=dy_path["src"].replace("/", "\\")
                dy_path["dst"]=dy_path["dst"].replace("/", "\\")

                if not os.path.exists(dy_path["direpa_dst"]):
                    os.makedirs(dy_path["direpa_dst"], exist_ok=True)

                if dy_path["type"] == "file":
                    cmd=[
                        "copy",
                        "/Y",
                        dy_path["src"],
                        dy_path["dst"],
                    ]
                elif dy_path["type"] == "dir":
                    cmd=[
                        filenpa_msdeploy,
                        "-verb:sync",
                        r"-source:dirPath={}".format(dy_path["src"]),
                        r"-dest:dirPath={}".format(dy_path["dst"]),
                    ]
                shell.cmd_prompt(cmd)

    msg.success("deploy completed")

def winscp_cmd(winscp_profile, cmd, fail=True):
    filenpa_tmp=tempfile.TemporaryFile().name
    msg.info(cmd)
    with open(filenpa_tmp, "w") as f:
        f.write("{}\n".format(cmd))
        f.write("exit\n")
    cmd=[
        "winscp.com",
        winscp_profile,
        "/script={}".format(filenpa_tmp),
    ]
    proc=subprocess.Popen(cmd)
    stdout, stderr=proc.communicate()
    os.remove(filenpa_tmp)

    if fail is True:
        if proc.returncode != 0:
            msg.error("failed '{}'".format(cmd), exit=1)

    return proc.returncode

def get_paths(
    direpa_deploy,
    direpa_publish,
    push_paths,
):
    direpa_publish=direpa_publish.replace("\\", "/")
    direpa_deploy=direpa_deploy.replace("\\", "/")

    if isinstance(push_paths, str):
        push_paths=[push_paths]

    dy_paths=[]
    if push_paths is not None:
        for elem in push_paths:
            elem=elem.replace("\\\\", "\\").replace("\\", "/")
            if isinstance(elem, str):
                dy_path=dict()
                path_src=elem
                if os.path.isabs(elem) is False:
                    path_src=os.path.join(direpa_publish, elem)

                if not os.path.exists(path_src):
                    msg.error("push paths src not found '{}'".format(path_src), exit=1)

                dy_path["src"]=os.path.normpath(path_src).replace("\\", "/")
                dy_path["type"]=None
                if os.path.isdir(path_src):
                    dy_path["type"]="dir"
                elif os.path.isfile(path_src):
                    dy_path["type"]="file"
                else:
                    msg.error("push paths src is not a file or a dir '{}'".format(path_src), exit=1)

                path_rel=re.sub(r"^{}/".format(direpa_publish), "", dy_path["src"])
                if path_rel == dy_path["src"]:
                    msg.error("push paths src impossible to extract path_rel from '{}'".format(path_src), exit=1)

                dy_path["dst"]=os.path.join(direpa_deploy, path_rel).replace("\\", "/")
                dy_path["direpa_dst"]=os.path.dirname(dy_path["dst"])

                dy_paths.append(dy_path)

            elif isinstance(elem, dict):
                msg.error("push paths dict function not implement yet", exit=1)
                # "here" puth a check on direpa_deploy and dst if different then error
                pass
            else:
                msg.error("push paths expected list or str not '{}' with '{}'".format(type(elem), elem), exit=1)

    if len(dy_paths) > 0:
        return dy_paths
    else:
        return None

def set_web_config(direpa_publish, webconfigs):
    filenpa_webconfig=os.path.join(direpa_publish, "Web.config")
    update_webconfig=False
    xml_tree=etree.parse(filenpa_webconfig)
    root=xml_tree.getroot()

    for wconf in webconfigs:
        xml_elem=None
        current_value=None
        new_value=None
        attr=None

        if wconf in [ "bundle-off", "bundle-on"]:
            xml_elem=root.find("./appSettings/add[@key='BUNDLE']")
            current_value=xml_elem.attrib["value"]
            if wconf[-2:] == "on":
                new_value="true"
            elif wconf[-3:] == "off":
                new_value="false"
            attr="value"
        elif wconf in [ "custom-off", "custom-on"]:
            xml_elem=root.find("./system.web/customErrors[@mode]")
            current_value=xml_elem.attrib["mode"]
            if wconf[-2:] == "on":
                new_value="On"
            elif wconf[-3:] == "off":
                new_value="Off"
            attr="mode"
        elif wconf in [ "debug-off", "debug-on"]:
            xml_elem=root.find("./system.web/compilation[@debug]")
            current_value=xml_elem.attrib["debug"]
            if wconf[-2:] == "on":
                new_value="true"
            elif wconf[-3:] == "off":
                new_value="false"
            attr="debug"

        if current_value != new_value:
            xml_elem.attrib[attr]=new_value
            update_webconfig=True

    if update_webconfig is True:
        xml_tree.write(filenpa_webconfig)
        print("Web.config updated")

    return update_webconfig