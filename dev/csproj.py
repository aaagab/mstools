#!/usr/bin/env python3
from datetime import datetime
from pprint import pprint
import json
import glob
from lxml import etree
import os
import re
import sys
import urllib.parse

def get_dy_csproj(
    direpa_root=None
):
    if direpa_root is None:
        direpa_root=os.getcwd()
    dy_csproj=dict()

    filens_csproj=glob.glob(os.path.join(direpa_root, "*.csproj"))
    dy_csproj["filen_csproj"]=""

    if filens_csproj:
        if len(filens_csproj) != 1:
            print("Multiple csproj in '{}'".format(direpa_root))
            print("Select only one")
            for filen in filens_csproj:
                print(filen)
            sys.exit(1)
        dy_csproj["filen_csproj"]=filens_csproj[0]
    else:
        print("No csproj file found in '{}'".format(direpa_root))
        sys.exit()

    dy_csproj["direpa_root"]=direpa_root
    dy_csproj["filenpa_csproj"]=os.path.join(direpa_root, dy_csproj["filen_csproj"])
    dy_csproj["filenpa_log"]=os.path.join(direpa_root, "Logs", "log.txt")

    dy_csproj["csproj_xml_tree"]=get_xml_tree(dy_csproj["filenpa_csproj"])
    root=dy_csproj["csproj_xml_tree"].getroot()
    dy_csproj["xml_root_namespace"]=root.find(".//PropertyGroup/RootNamespace", namespaces=root.nsmap).text
    dy_csproj["assembly_name"]=root.find(".//PropertyGroup/AssemblyName", namespaces=root.nsmap).text
    dy_csproj["filen_assembly"]=dy_csproj["assembly_name"]+".dll"
    dy_csproj["filenpa_assembly"]=os.path.join(direpa_root, "bin", dy_csproj["filen_assembly"])
    dy_csproj["app_name"]=dy_csproj["assembly_name"].lower()

    return dy_csproj

def get_xml_tree(filenpa):
    parser=etree.XMLParser(remove_blank_text=True)
    return etree.parse(filenpa, parser)
              
def get_all_build_paths( 
    direpa_root,
    root=True, 
    build_paths=None, 
    direpa="",
    excluded_bin_extensions=None,
    excluded_bin_files=None,
    excluded_bin_folders=None,
    included_bin_extensions=None,
):
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
    
    if not direpa:
        direpa=direpa_root

    elems=os.listdir(direpa)
    if elems:
        for elem_name in elems:
            elem_path=os.path.join(direpa, elem_name)
            relpath=os.path.relpath(elem_path, direpa_root)
            if relpath not in excluded_bin_folders:
                if os.path.isdir(elem_path):
                    get_all_build_paths(
                        # direpa_root, False, build_paths, elem_path,
                        direpa_root=direpa_root,
                        root=False, 
                        build_paths=build_paths,
                        direpa=elem_path,
                        excluded_bin_extensions=excluded_bin_extensions,
                        excluded_bin_files=excluded_bin_files,
                        excluded_bin_folders=excluded_bin_folders,
                        included_bin_extensions=included_bin_extensions,
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

    if root is True:
        return build_paths

def csproj_backup(
    direpa_root,
    filenpa_csproj
):
    import shutil

    direpa_csproj_backup=os.path.join(direpa_root, "_csproj_backup")
    if not os.path.exists(direpa_csproj_backup):
        os.mkdir(direpa_csproj_backup)

    date_prefix=datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-5]
    filen_backup="{}_{}".format(date_prefix, os.path.basename(filenpa_csproj))
    filenpa_backup=os.path.join(direpa_csproj_backup, filen_backup)
    shutil.copyfile(filenpa_csproj, filenpa_backup)
    print("'{}' backed-up".format(os.path.basename(filenpa_csproj)))
    for f, filen in enumerate(sorted(os.listdir(direpa_csproj_backup), reverse=True)):
        if f >= 20:
            os.remove(os.path.join(direpa_csproj_backup, filen))
    # keep only the latest 20 files

def csproj_update(
    csproj_xml_tree,
    direpa_root,
    filenpa_csproj,
):
    test=False
    # test=True
    if test is True:
        filenpa_out=os.path.join(os.environ["userprofile"], "fty", "bin", "msbuild", "dev", "draft", "out.xml")
    else:
        csproj_backup(
            direpa_root,
            filenpa_csproj,
        )
        filenpa_out=filenpa_csproj

    csproj_xml_tree.write(filenpa_out, encoding='utf-8', xml_declaration=True, pretty_print=True)
    if test is False:
        print("Updated '{}'".format(filenpa_csproj))

def get_xml_str_without_namespace(xml_tree, xml_elem):
    xml_string=etree.tostring(xml_elem, pretty_print=True).decode()
    for name, ns in xml_tree.getroot().nsmap.items():
        xml_string=re.sub(r"\sxmlns=\"{}\"".format(ns), "", xml_string)
    return xml_string.rstrip()

def get_build_xml_nodes_csproj(
    csproj_xml_tree, 
    ignore=None,
):

    if ignore is None:
        ignore=["log.txt"]
    xml_nodes=[]
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
                    filen=os.path.basename(urllib.parse.unquote(elem.attrib["Include"]))
                    if filen not in ignore:
                    # filenpa_rel=urllib.parse.unquote(xml_node.attrib["Include"])
                    # filenpa=os.path.join(direpa_root, filenpa_rel)
                        xml_nodes.append(elem)

    return xml_nodes
