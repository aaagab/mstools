#!/usr/bin/env python3
import glob
import json
from lxml import etree
from pprint import pprint
import os
import re
import subprocess
import shutil
import sys
import tempfile
# import threading

from ..gpkgs import message as msg
from ..gpkgs import shell_helpers as shell
from ..gpkgs.prompt import prompt_boolean

def check_direpa_ftp_exists(winscp_profile, direpa_ftp, prompt_directory):
    if winscp_cmd(winscp_profile, "stat {}".format(direpa_ftp), fail=False) == 1:
        if prompt_directory is True:
            msg.warning("Not found: {}".format(direpa_ftp))
            if prompt_boolean("Do you want to create that folder on ftp"):
                winscp_cmd(winscp_profile, "mkdir \"{}\"".format(direpa_ftp), fail=True)
                msg.success("Created '{}'".format(direpa_ftp))
            else:
                msg.error("ftp path not found '{}'".format(direpa_ftp), exit=1)
        else:
            msg.error("ftp path not found '{}'".format(direpa_ftp), exit=1)

def deploy(
    deploy_path,
    direpa_publish,
    filenpa_msdeploy,
    exclude_paths,
    include_paths,
):
    cmd=[]
    filenpa_tmp=None
    success=False

    if deploy_path is None:
        msg.error("deploy path is not set for selected profile.", exit=1)

    if deploy_path[:6] == "ftp://":
        exclude_default_paths=[
            "App_Data/log.txt", 
            "Uploads/", 
            "Logs/",
        ]

        winscp_profile=deploy_path[6:].split("/")[0]
        direpa_ftp_dst=deploy_path[6+len(winscp_profile):].replace("\\", "/")
        deploy_paths=get_paths(direpa_ftp_dst, direpa_publish, include_paths)

        check_direpa_ftp_exists(winscp_profile, direpa_ftp_dst, prompt_directory=False)
        filemask=get_filemask(direpa_publish, direpa_ftp_dst, exclude_paths, exclude_default_paths)
        cmd_sync=r'synchronize remote -mirror -delete -criteria=time -transfer=automatic{} "{{}}" "{{}}"'.format(" "+filemask)

        if deploy_paths is None:
            cmd=cmd_sync.format(
                direpa_publish,
                direpa_ftp_dst,
            )
            winscp_cmd(winscp_profile, cmd, fail=True)
        else:
            for dy_path in deploy_paths:
                if dy_path["type"] == "file":
                    cmd="put \"{}\" \"{}\"".format(
                        dy_path["src"].replace("/", "\\"),
                        os.path.dirname(dy_path["dst"])+"/",
                    )
                    winscp_cmd(winscp_profile, cmd, fail=False)
                elif dy_path["type"] == "dir":
                    cmd=cmd_sync.format(
                        dy_path["src"],
                        dy_path["dst"],
                    )
                    if winscp_cmd(winscp_profile, cmd, fail=False) == 1:
                        check_direpa_ftp_exists(winscp_profile, dy_path["dst"], prompt_directory=True)
                        winscp_cmd(winscp_profile, cmd, fail=True)
    else:
        print(deploy_path)
        deploy_path=os.path.normpath(deploy_path)
        deploy_paths=get_paths(deploy_path, direpa_publish, include_paths)

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

def get_filemask(direpa_src, direpa_dst, exclude_paths, exclude_default_paths):
    dy_paths=dict(
        abs=[],
        rel=[],
    )

    tmp_direpa_src=direpa_src.replace("\\", "/")
    tmp_direpa_dst=direpa_dst.replace("\\", "/")

    for tmp_path in exclude_paths:
        found=False
        if os.path.isabs(tmp_path):
            msg.error("for --deploy --exclude path must be relative '{}'".format(tmp_path), exit=1)
            if tmp_path[0] in ["\\", "/"]:
                tmp_path=tmp_path[1:]
        path_rel_elem_user=tmp_path.replace("\\", "/")
        level_user=path_rel_elem_user.count("/")+1

        for path, directories, files in os.walk(direpa_src):
            path_rel=path.replace(direpa_src, "").replace("\\", "/")
            
            if len(path_rel) > 0:
                if path_rel[0] == "/":
                    path_rel=path_rel[1:]

            level=1
            if len(path_rel) > 0:
                if "/" in path_rel:
                    level=len(path_rel.split("/"))+1
                else:
                    level=2

            if level < level_user:
                continue
            elif level == level_user:
                count=0
                for elems in [directories, files]:
                    for elem in elems:
                        path_rel_elem=os.path.join(path_rel, elem).replace("\\", "/")
                        if path_rel_elem.lower() == path_rel_elem_user.lower():
                            found=True
                            tmp_str=path_rel_elem
                            if count == 0:
                                tmp_str+="/"
                            dy_paths["rel"].append(tmp_str)
                            break
                    count+=1
                    if found is True:
                        break
                if found is True:
                    break
            else:
                pass
        
        if found is False:
            msg.error("for --deploy --exclude relative path not found '{}'".format(tmp_path), exit=1)

    has_paths=False
    dy_paths["rel"].extend(exclude_default_paths)

    for rel_path in dy_paths["rel"]:
        has_paths=True
        rel_path=rel_path.replace("\\", "/")
        dy_paths["abs"].append("{}/{}".format(tmp_direpa_src, rel_path))
        dy_paths["abs"].append("{}/{}".format(tmp_direpa_dst, rel_path))

    filemask=""
    if has_paths is True:
        filemask="-filemask=\" | {}\"".format("; ".join(sorted(dy_paths["abs"])))

    return filemask

def winscp_cmd(winscp_profile, cmd, fail):
    filenpa_tmp=tempfile.TemporaryFile().name
    msg.info(cmd)
    with open(filenpa_tmp, "w") as f:
        f.write("{}\n".format(cmd))
        f.write("exit\n")
    tmp_cmd=[
        "winscp.com",
        winscp_profile,
        "/script={}".format(filenpa_tmp),
    ]
    proc=subprocess.Popen(tmp_cmd)
    proc.communicate()
    os.remove(filenpa_tmp)
    if fail is True:
        if proc.returncode != 0:
            msg.error("failed '{}'".format(tmp_cmd), exit=1)
    return proc.returncode

def get_paths(
    direpa_deploy,
    direpa_publish,
    include_paths,
):
    direpa_publish=direpa_publish.replace("\\", "/")
    direpa_deploy=direpa_deploy.replace("\\", "/")

    # if isinstance(include_paths, str):
        # include_paths=[include_paths]

    dy_paths=[]
    if include_paths is not None:
        for elem in include_paths:
            elem=elem.replace("\\\\", "\\").replace("\\", "/")
            # if isinstance(elem, str):
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

            # elif isinstance(elem, dict):
                # msg.error("push paths dict function not implement yet", exit=1)
                # # "here" puth a check on direpa_deploy and dst if different then error
                # pass
            # else:
                # msg.error("push paths expected list or str not '{}' with '{}'".format(type(elem), elem), exit=1)

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