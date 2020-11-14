#!/usr/bin/env python3
from ctypes import windll, Structure, c_long, byref
from lxml import etree
from pprint import pprint

import json
import os
import shutil
import subprocess
import sys
import tempfile

from .csproj_update import csproj_update_files, is_project_need_build
from .get_profile import get_profile

from ..gpkgs import message as msg

def publish(
    app_name,
    debug,
    direpa_publish,
    direpa_root,
    csproj_xml_tree,
    filenpa_assembly,
    filenpa_cache_assembly,
    filenpa_csproj,
    filenpa_log,
    filenpa_msbuild,
    profile_name,
    rebuild_mode,
    set_doc,
):
 
    if set_doc is True:
        set_documentation(direpa_root)

    # debug and proxy configuration share the same path and thus the same pm2 instance. however to use either or the other, the application must be republished
    # because they don't have the same web.config and base_path is going to cause an infifinte loop in the browser.
    # debug open at http://localhost:port
    # proxy open at https://www.edu

    os.makedirs(direpa_publish, exist_ok=True)

    csproj_update_files(
        csproj_xml_tree,
        debug,
        direpa_root,
        filenpa_csproj,
    )

    rebuild_frontend=False
    rebuild_fullstack=False

    if rebuild_mode == "frontend":
        rebuild_frontend=True
    elif rebuild_mode == "fullstack":
        rebuild_fullstack=True
    elif rebuild_mode == "any":
        ### is_project_need_build, 
        # I also need to check if project need pushed.
        # because if database has been updated then project needs to be pushed again.
        filenpa_publish_assembly=os.path.join(direpa_publish, "bin", os.path.basename(filenpa_assembly))
        if not os.path.exists(filenpa_publish_assembly):
            rebuild_fullstack=True
        else:
            previous_profile=get_webconfig_profile(direpa_publish)
            if previous_profile is None or previous_profile != profile_name:
                rebuild_fullstack=True

        if rebuild_fullstack is False:
            filenpas=is_project_need_build(
                debug,
                direpa_root,
                csproj_xml_tree,
                filenpa_assembly,
                filenpa_csproj,
                return_filenpas=True
            )

            for filenpa in filenpas:
                filenrel=os.path.relpath(filenpa, direpa_root)
                elems=filenrel.split(os.sep)
                if len(elems) > 1 and elems[0] == "App":
                    rebuild_frontend=True
                else:
                    rebuild_fullstack=True
                    break

            if rebuild_frontend is False and rebuild_fullstack is False:
                date_filenpa_publish_assembly=os.path.getmtime(filenpa_publish_assembly)
                date_filenpa_assembly=os.path.getmtime(filenpa_assembly)
                if date_filenpa_assembly > date_filenpa_publish_assembly:
                    rebuild_fullstack=True
                
    if rebuild_fullstack is True:
        # make sure these files are recreated for new check on is_project_need_build, they are the reference date to decide if is_project_need_build
        for filenpa in [
            filenpa_assembly,
            filenpa_cache_assembly,
        ]:
            if os.path.exists(filenpa):
                os.remove(filenpa)

        # clear logs
        if os.path.exists(filenpa_log):
            open(filenpa_log, "w").close()

        cmd=[
            filenpa_msbuild,
            filenpa_csproj,
            # "/v:diagnostic",
            # "/v:detailed",
            "/v:Normal",
            "/nologo",
            "/m",
            "/p:Configuration={}".format(profile_name.capitalize()),
            "/p:DeleteExistingFiles=True",
            "/p:DeployOnBuild=True",
            "/p:ExcludeApp_Data=False",
            "/p:LaunchSiteAfterPublish=False",
            "/p:PublishProvider=FileSystem",
            "/p:PublishProfile={}".format(profile_name),
            "/p:publishUrl={}".format(direpa_publish),
            # "/p:publishUrl={}".format(r"A:\wrk\e\example\1\src\_publish\proxy"),
            "/p:WebPublishMethod=FileSystem",
            # r"/p:WebPublishPipelineCustomizeTargetFile=A:\wrk\e\example\1\src\example.wpp.targets",
            # r"/p:MSDeployPublishSetParametersFile=C:\Users\user\AppData\Local\Temp\test.xml",
            # "/p:SkipExtraFilesOnServer=True",
            # '/p:ExcludeFoldersFromDeployment=Uploads',
            # "-skip:Directory=\\\\App_Data",
        ]

        pprint(cmd)
        process=subprocess.Popen(cmd)
        process.communicate()
      
        if process.returncode == 0:
            print()
            print("msbuild.exe success")
            return True
        else:
            sys.exit(1)

    elif rebuild_frontend is True:
        direpa_root_client=os.path.join(direpa_root, "s")
        direpa_publish_client=os.path.join(direpa_publish, "App")
        os.system(r'robocopy "{}" "{}" /MIR /FFT /Z /XA:H /W:5 /njh /njs /ndl /nc /ns'.format(direpa_root_client, direpa_publish_client))
        print("robocopy success")
        return True
        # deploy_path_client=os.path.join(deploy_path, "App")
        # os.system(r'robocopy "{}" "{}" /MIR /FFT /Z /XA:H /W:5 /njh /njs /ndl /nc /ns'.format(direpa_publish_client, deploy_path_client))
        # print("Front End updated")
    else:
        msg.info("Publishing Project '{}' is already up-to-date".format(app_name))
        return False
    
def get_webconfig_profile(direpa_publish):
    filenpa_webconfig=os.path.join(direpa_publish, "Web.config")
    if not os.path.exists(filenpa_webconfig):
        return None

    xml_tree=etree.parse(filenpa_webconfig)
    root=xml_tree.getroot()
    # <add key="MODE" value="proxy" />
    xml_elem=root.find("./appSettings/add[@key='MODE']")
    if xml_elem is None:
        return None
    else:
        xml_elem_azure=root.find("./appSettings/add[@key='FROM_AZURE']")
        # I add to create different profile because we use azure
        if xml_elem_azure is not None:
            return "my{}".format(xml_elem.attrib["value"])

    return xml_elem.attrib["value"]
    
def zip_release(app_name, direpa_publish):
    filenpa_version=os.path.join(direpa_publish, "version.txt")
    version=None
    with open(filenpa_version, "r") as f:
        version=f.read().strip()

    filer_release="{}-{}".format(app_name, version)
    direpa_publish_parent=os.path.dirname(direpa_publish)
    filerpa_release=os.path.join(direpa_publish_parent, filer_release)
    filenpa_release=filerpa_release+".zip"
    if os.path.exists(filenpa_release):
        print("File Already Exists '{}'".format(filenpa_release))
        print("Change App Version or Delete File")
        sys.exit(1)

    shutil.make_archive(filerpa_release, 'zip', direpa_publish)
    print("File created '{}'".format(filenpa_release))

def set_documentation(direpa_root):
    direpa_src=os.path.join(direpa_root)
    direpa_src_documentation=os.path.join(os.path.dirname(direpa_src), "doc", "release")

    if os.path.exists(direpa_src_documentation):
        direpa_dst_documentation=os.path.join(direpa_root, "App_Data", "documentation")
        if os.path.exists(direpa_dst_documentation):
            shutil.rmtree(direpa_dst_documentation)
        os.makedirs(direpa_dst_documentation)
        synchronize_documentation(direpa_src_documentation, direpa_dst_documentation)
        print("Documentation synchronized")

def synchronize_documentation(direpa_src, direpa_dst):
    for elem in os.listdir(direpa_src):
        path_elem_src=os.path.join(direpa_src, elem)
        path_elem_dst=os.path.join(direpa_dst, elem)
        if os.path.isfile(path_elem_src):
            shutil.copyfile(path_elem_src, path_elem_dst)
        else:
            os.makedirs(path_elem_dst)
            synchronize_documentation(path_elem_src, path_elem_dst)

def get_mouse_position():
    class POINT(Structure):
        _fields_ = [("x", c_long), ("y", c_long)]

    def queryMousePosition():
        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))
        return { "x": pt.x, "y": pt.y}

    pos = queryMousePosition()
    print(pos)