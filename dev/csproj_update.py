#/usr/bin/env python3
from pprint import pprint
import os
import sys
import urllib.parse
import subprocess

from lxml.etree import _ElementTree

from .csproj import Csproj
from .csproj_clean_files import csproj_clean_files
from .csproj_add_files import csproj_add_files
from .csproj import get_build_xml_nodes_csproj, get_xml_tree

def csproj_update_files(
    csproj:Csproj,
    force:bool=False,
):
    if csproj.debug is True:
        print("updating '{}'".format(os.path.basename(csproj.filenpa_csproj)))

    next_xml_tree=csproj.xml_tree
    if csproj_clean_files(
        csproj,
        force,
    ) is True:
        next_xml_tree=get_xml_tree(csproj.filenpa_csproj)

    csproj_add_files(
        csproj=csproj,
        csproj_xml_tree=next_xml_tree,
        force=force,
    )

def is_file_to_yield(debug:bool, date_build:float, filenpa:str):
    date_filenpa=os.path.getmtime(filenpa)
    if date_filenpa > date_build:
        if debug is True:
            print("{:<18}".format(date_filenpa), filenpa)
        return True
    else:
        return False

def get_to_build_files(
    csproj:Csproj,
    filenpas:list[str]|None=None,
):
    if os.path.exists(csproj.filenpa_assembly):
        date_build=os.path.getmtime(csproj.filenpa_assembly)
        if csproj.debug is True:
            print()
            print("{:<18}".format(date_build), csproj.filenpa_assembly)
            print()

        if filenpas is None:
            for xml_node in get_build_xml_nodes_csproj(csproj.xml_tree, csproj.ignore_csproj_paths):
                filenpa_rel=urllib.parse.unquote(xml_node.attrib["Include"])
                filenpa=os.path.join(csproj.direpa_root, filenpa_rel)
                if is_file_to_yield(csproj.debug, date_build, filenpa):
                    yield filenpa
            if is_file_to_yield(csproj.debug, date_build, csproj.filenpa_csproj):
                yield csproj.filenpa_csproj
        else:
            for filenpa in filenpas:
                if is_file_to_yield(csproj.debug, date_build, filenpa):
                    yield filenpa
    else:
        for xml_node in get_build_xml_nodes_csproj(csproj.xml_tree, csproj.ignore_csproj_paths):
            filenpa_rel=urllib.parse.unquote(xml_node.attrib["Include"])
            filenpa=os.path.join(csproj.direpa_root, filenpa_rel)
            yield filenpa
        yield csproj.filenpa_csproj

def is_project_need_build(
    csproj:Csproj,
    filenpas:list[str]|None=None,
):
    if not os.path.exists(csproj.filenpa_assembly):
        return True
    else:
        for filenpa in get_to_build_files(
            csproj=csproj,
            filenpas=filenpas,
        ):
            return True

    return False

def build_project(
    csproj:Csproj,
    filenpa_msbuild:str,
    force_build:bool=False,
    force_csproj:bool=False,
):
    csproj_update_files(
        csproj=csproj,
        force=force_csproj,
    )
    if force_build is True:
        build_execute(
            csproj.filenpa_csproj,
            filenpa_msbuild,
        )
    else:
        if is_project_need_build(
            csproj=csproj,
        ):    
            build_execute(
                csproj.filenpa_csproj,
                filenpa_msbuild,
            )
        else:
            print("No build needed.")

def build_execute(
    filenpa_csproj:str,
    filenpa_msbuild:str,
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