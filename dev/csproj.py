#!/usr/bin/env python3
from typing import cast
from copy import deepcopy
from pprint import pprint
from datetime import datetime, timezone
import json
import glob
from lxml import etree
from lxml.etree import _ElementTree, _Element
import os
import re
import shutil
import sys
import urllib.parse
from ..gpkgs.timeout import TimeOut

class Csproj():
    def __init__(self,
        direpa_root:str,
        filen_csproj:str,
        debug:bool=False,
    ):
        self.debug=debug
        self.direpa_root=direpa_root
        self.filenpa_csproj=os.path.join(direpa_root, filen_csproj)

        self.excluded_bin_folders:list[str]=[]
        self.excluded_bin_files:list[str]=[]
        self.excluded_bin_extensions:list[str]=[]
        self.excluded_bin_paths:list[str]=[]
        self.ignore_csproj_paths:list[str]=[]
        filenpa_user_settings=os.path.join(direpa_root, ".mstools.json")
        if os.path.exists(filenpa_user_settings):
            with open(filenpa_user_settings, "r") as f:
                dy=json.load(f)
                if "excluded_bin_folders" in dy and isinstance(dy["excluded_bin_folders"], list):
                    for elem in dy["excluded_bin_folders"]:
                        if isinstance(elem, str):
                            self.excluded_bin_folders.append(os.path.normpath(elem))
                if "excluded_bin_files" in dy and isinstance(dy["excluded_bin_files"], list):
                    for elem in dy["excluded_bin_files"]:
                        if isinstance(elem, str):
                            self.excluded_bin_files.append(os.path.normpath(elem))
                if "excluded_bin_extensions" in dy and isinstance(dy["excluded_bin_extensions"], list):
                    for elem in dy["excluded_bin_extensions"]:
                        if isinstance(elem, str):
                            self.excluded_bin_extensions.append(os.path.normpath(elem))
                if "excluded_bin_paths" in dy and isinstance(dy["excluded_bin_paths"], list):
                    for elem in dy["excluded_bin_paths"]:
                        if isinstance(elem, str):
                            self.excluded_bin_paths.append(os.path.normpath(elem))
                if "ignore_csproj_paths" in dy and isinstance(dy["ignore_csproj_paths"], list):
                    for elem in dy["ignore_csproj_paths"]:
                        if isinstance(elem, str):
                            self.ignore_csproj_paths.append(os.path.normpath(elem))

        self.filenpa_log=os.path.join(direpa_root, "Logs", "log.txt")
        self.update_tree(get_xml_tree(self.filenpa_csproj))

    def update_tree(self, xml_tree:_ElementTree):
        self.xml_tree=xml_tree
        root=self.xml_tree.getroot()
        nsmap = get_nsmap(root)
        xml_root_namespace=root.find(".//PropertyGroup/RootNamespace", namespaces=nsmap)
        if xml_root_namespace is None:
            raise Exception(f"In file '{self.filenpa_csproj}' .//PropertyGroup/RootNamespace not found.")
        if xml_root_namespace.text is None:
            raise Exception(f"In file '{self.filenpa_csproj}' .//PropertyGroup/RootNamespace value must be set.")
        self.xml_root_namespace=xml_root_namespace.text
        assembly_name=root.find(".//PropertyGroup/AssemblyName", namespaces=nsmap)
        if assembly_name is None:
            raise Exception(f"In file '{self.filenpa_csproj}' .//PropertyGroup/AssemblyName not found.")
        if assembly_name.text is None:
            raise Exception(f"In file '{self.filenpa_csproj}' .//PropertyGroup/AssemblyName value must be set.")
        self.assembly_name=assembly_name.text
        self.filen_assembly=self.assembly_name+".dll"
        self.filenpa_assembly=os.path.join(self.direpa_root, "bin", self.filen_assembly)
        self.app_name=self.assembly_name.lower()

    def to_json(self):
        obj=deepcopy(self)
        setattr(obj, "xml_tree", "")
        return json.dumps(obj, default=lambda o: o.__dict__, indent=4, sort_keys=True)
    
    def write(self, xml_tree:_ElementTree):
        self.update_tree(xml_tree=xml_tree)
        self.backup()

        timer=TimeOut(2).start()
        loop=True
        while True:
            if timer.has_ended(pause=.001):
                loop=False
            try:
               xml_tree.write(self.filenpa_csproj, encoding='utf-8', xml_declaration=True, pretty_print=True)
               break
            except PermissionError as e:
                if loop is True:
                    continue
                else:
                    raise
            
        xml_tree.write(self.filenpa_csproj, encoding='utf-8', xml_declaration=True, pretty_print=True)
        print("Updated '{}'".format(self.filenpa_csproj))

    def backup(self):
        direpa_csproj_backup=os.path.join(self.direpa_root, "_csproj_backup")
        if not os.path.exists(direpa_csproj_backup):
            os.mkdir(direpa_csproj_backup)

        date_prefix=datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:-5]
        filen_backup="{}_{}".format(date_prefix, os.path.basename(self.filenpa_csproj))
        filenpa_backup=os.path.join(direpa_csproj_backup, filen_backup)
        shutil.copyfile(self.filenpa_csproj, filenpa_backup)
        print("'{}' backed-up".format(os.path.basename(self.filenpa_csproj)))
        for f, filen in enumerate(sorted(os.listdir(direpa_csproj_backup), reverse=True)):
            # keep only the latest 20 files
            if f >= 20:
                os.remove(os.path.join(direpa_csproj_backup, filen))

def get_xml_str_without_namespace(xml_tree:_ElementTree, xml_elem:_Element):
    xml_string=etree.tostring(xml_elem, pretty_print=True).decode()
    for name, ns in xml_tree.getroot().nsmap.items():
        xml_string=re.sub(r"\sxmlns=\"{}\"".format(ns), "", xml_string)
    return xml_string.rstrip()

def get_build_xml_nodes_csproj(
    csproj_xml_tree:_ElementTree, 
    ignore_csproj_paths:list[str]|None=None,
):
    if ignore_csproj_paths is None:
        ignore_csproj_paths=[]

    xml_nodes:list[_Element]=[]
    for elem in csproj_xml_tree.iter():
        if elem.tag is not etree.Comment:
            tag=etree.QName(elem).localname
            if tag in [
                "Compile",
                "Content",
                "Folder",
                "None",
                "EmbeddedResource"
                ]:
                if "Include" in elem.attrib:
                    filen=os.path.basename(os.path.normpath(urllib.parse.unquote(elem.attrib["Include"])))
                    if filen not in ignore_csproj_paths:
                        xml_nodes.append(elem)

    return xml_nodes

def get_csproj(
    debug:bool,
    direpa_root:str|None=None
):
    if direpa_root is None:
        direpa_root=os.getcwd()

    filens_csproj=glob.glob(os.path.join(direpa_root, "*.csproj"))
    filen_csproj=""

    if filens_csproj:
        if len(filens_csproj) != 1:
            print("Multiple csproj in '{}'".format(direpa_root))
            print("Select only one")
            for filen in filens_csproj:
                print(filen)
            sys.exit(1)
        filen_csproj=filens_csproj[0]
    else:
        print("No csproj file found in '{}'".format(direpa_root))
        sys.exit(1)

    csproj=Csproj(debug=debug, direpa_root=direpa_root, filen_csproj=filen_csproj)
    return csproj

def get_xml_tree(filenpa:str) -> _ElementTree:
    parser=etree.XMLParser(remove_blank_text=True)
    elem=etree.parse(filenpa, parser)
    if isinstance(elem, _ElementTree) is False:
        raise Exception(f"Can't return _ElementTree from file '{filenpa}'")
    return elem
              
def get_nsmap(root:_Element):
    nsmap = {k if k is not None else '':v for k,v in root.nsmap.items()}
    return nsmap

def get_all_build_paths( 
    direpa_root:str,
    build_paths:set[str]|None=None, 
    direpa:str="",
    excluded_bin_extensions:list[str]|None=None,
    excluded_bin_files:list[str]|None=None,
    excluded_bin_folders:list[str]|None=None,
    included_bin_extensions:list[str]|None=None,
    excluded_bin_paths:list[str]|None=None,
) -> set[str]:
    if build_paths is None:
        build_paths=set()

    if excluded_bin_extensions is None:
        excluded_bin_extensions=[]
    if excluded_bin_files is None:
        excluded_bin_files=[]
    if excluded_bin_folders is None:
        excluded_bin_folders=[]
    if included_bin_extensions is None:
        included_bin_extensions=[]
    if excluded_bin_paths is None:
        excluded_bin_paths=[]

    if not direpa:
        direpa=direpa_root

    elems=os.listdir(direpa)
    if elems:
        for elem_name in elems:
            elem_path=os.path.join(direpa, elem_name)
            relpath=os.path.relpath(elem_path, direpa_root)
            if elem_path not in excluded_bin_paths:
                if relpath not in excluded_bin_folders:
                    if os.path.isdir(elem_path):
                        get_all_build_paths(
                            direpa_root=direpa_root,
                            build_paths=build_paths,
                            direpa=elem_path,
                            excluded_bin_extensions=excluded_bin_extensions,
                            excluded_bin_files=excluded_bin_files,
                            excluded_bin_folders=excluded_bin_folders,
                            included_bin_extensions=included_bin_extensions,
                            excluded_bin_paths=excluded_bin_paths,
                        )
                    else:
                        filen=os.path.basename(elem_path)
                        if filen not in excluded_bin_files:
                            filext=os.path.splitext(filen)[1]
                            if filext not in excluded_bin_extensions:
                                if len(included_bin_extensions) > 0:
                                    if filext in included_bin_extensions:
                                        build_paths.add(elem_path)
                                else:
                                    build_paths.add(elem_path)
    else:
        if direpa not in excluded_bin_folders:
            build_paths.add(direpa)

    return build_paths
