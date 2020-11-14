#/usr/bin/env python3
from pprint import pprint
import os
import sys
import urllib.parse
import subprocess

from .csproj_clean_files import csproj_clean_files
from .csproj_add_files import csproj_add_files
from .csproj import get_build_xml_nodes_csproj, get_xml_tree


def csproj_update_files(
    csproj_xml_tree,
    debug,
    direpa_root,
    filenpa_csproj,
):
    if debug is True:
        print("updating '{}'".format(os.path.basename(filenpa_csproj)))

    next_xml_tree=csproj_xml_tree
    if csproj_clean_files(
        csproj_xml_tree,
        debug,
        direpa_root,
        filenpa_csproj
    ) is True:
        next_xml_tree=get_xml_tree(filenpa_csproj)
    # csproj_xml needs to be regenerated
    csproj_add_files(
        next_xml_tree,
        debug,
        direpa_root,
        filenpa_csproj,
    )

# actually this part seems more complicated, because the main .dll can have been build before change to other files that does not need build.
# html on backend part are not part of the compile process they are just moved.


def is_project_need_build(
    debug,
    direpa_root,
    csproj_xml_tree,
    filenpa_assembly,
    filenpa_csproj,
    filenpas=None,
    filenpa_main=None,
    return_filenpas=False,
):
    need_build=False

    # print(direpa_root, csproj_xml_tree, filenpa_assembly, filenpa_csproj, return_filenpas)

    if filenpa_main is None:
        filenpa_main=filenpa_assembly

    if not os.path.exists(filenpa_main):
        if return_filenpas is True:
            filenpas=[]
            for xml_node in get_build_xml_nodes_csproj(csproj_xml_tree):
                filenpa_rel=urllib.parse.unquote(xml_node.attrib["Include"])
                filenpa=os.path.join(direpa_root, filenpa_rel)
                filenpas.append(filenpa)
            filenpas.append(filenpa_csproj)
            return filenpas
        else:
            return True
    else:
        date_build=os.path.getmtime(filenpa_main)
        # print()
        # print("{:<18}".format(date_build), filenpa_main)
        # print()

        if filenpas is None:
            filenpas=[]
            for xml_node in get_build_xml_nodes_csproj(csproj_xml_tree):
                filenpa_rel=urllib.parse.unquote(xml_node.attrib["Include"])
                filenpa=os.path.join(direpa_root, filenpa_rel)
                filenpas.append(filenpa)
            filenpas.append(filenpa_csproj)

        filenpas_modified=[]
        for filenpa in filenpas:
            date_filenpa=os.path.getmtime(filenpa)
            if date_filenpa > date_build:
                # print("{:<18}".format(date_filenpa), filenpa)
                filenpas_modified.append(filenpa)
                if return_filenpas is False:
                    if need_build is False:
                        if return_filenpas is True:
                            need_build=True
                        else:
                            return True
                        if debug is True:
                            print("\nFiles recently modified:")
                    if debug is True:
                        print(os.path.basename(filenpa))

    if return_filenpas is True:
        return filenpas_modified
    elif need_build:
        return True
    else:
        return False

# 1594359213.4478793 A:\wrk\e\example\1\src\bin\Example.dll

# 1594387704.5180898 A:\wrk\e\example\1\src\App\route.js
# 1594387443.5547745 A:\wrk\e\example\1\src\App\services\session.js
# 1594387337.219834  A:\wrk\e\example\1\src\App\app.js
# 1594385926.642794  A:\wrk\e\example\1\src\App\components\breadcrumb\breadcrumb.js
# 1594385897.6917233 A:\wrk\e\example\1\src\Views\Home\Index.cshtml

def build_project(
    debug,
    direpa_root,
    csproj_xml_tree,
    filenpa_assembly,
    filenpa_csproj,
    filenpa_msbuild,
    force=False
):
    csproj_update_files(
        csproj_xml_tree,
        debug,
        direpa_root,
        filenpa_csproj,
    )
    if force is True:
        build_execute(
            filenpa_csproj,
            filenpa_msbuild,
        )
    else:
        if is_project_need_build(
            debug,
			direpa_root,
			csproj_xml_tree,
			filenpa_assembly,
			filenpa_csproj,
        ):    
            build_execute(
                filenpa_csproj,
                filenpa_msbuild,
            )
        else:
            print("No build needed.")

def build_execute(
    filenpa_csproj,
    filenpa_msbuild,
):
    cmd=[]
    for elem in [
        filenpa_msbuild,
        filenpa_csproj,
        "/v:Normal",
        "/nologo",
        "/m",
        "/p:Configuration=Debug",
    ]:
        cmd.append(elem)
    pprint(cmd)
    process=subprocess.Popen(cmd)
    process.communicate()
    if process.returncode == 0:
        print("Project Rebuilt")
    else:
        sys.exit(1)