#/usr/bin/env python3
from copy import deepcopy
from pprint import pprint
import os
import re
import sys
import urllib.parse
from lxml import etree
from lxml.etree import _ElementTree, _Element

from .csproj import get_build_xml_nodes_csproj, get_all_build_paths, get_nsmap, Csproj

def csproj_add_files(
    csproj:Csproj,
    csproj_xml_tree:_ElementTree|None=None,
): # add, clean, update
    excluded_bin_folders=[
        ".git",
        ".vs",
        "_archives",
        "_runtime",
        "_migrations_sql",
        "_migrations_backup",
        "_tests",
        "_publish",
        "_sql",
        "_scripts",
        # "App_Data",
        "Logs",
        "archives",
        "bin",
        "obj",
        "packages",
        "_requests",
        "_db",
        "Tests",
        "ApexSources",
    ]
    excluded_bin_folders.extend(csproj.excluded_bin_folders)
    excluded_bin_files=[
        ".gitignore",
        ".yo-rc.json",
        "files.exclude",
        "hostname_url.txt",
        "log.txt",
        ".mstools.json",
    ]
    excluded_bin_files.extend(csproj.excluded_bin_files)
    excluded_bin_extensions=[
        ".csproj",
        ".user",
        ".sln",
        ".log",
        ".csproj_bak"
    ]
    excluded_bin_extensions.extend(csproj.excluded_bin_extensions)

    excluded_bin_paths=[]
    excluded_bin_paths.extend(csproj.excluded_bin_paths)
    tmp_excluded_bin_paths:list[str]=[]
    for elem in excluded_bin_paths:
        if os.path.isabs(elem) is False:
            elem=os.path.join(csproj.direpa_root, elem)
        elem=os.path.normpath(elem)
        tmp_excluded_bin_paths.append(elem)
    excluded_bin_paths=tmp_excluded_bin_paths

    filenpas_all=get_all_build_paths(
        direpa_root=csproj.direpa_root,
        excluded_bin_extensions=excluded_bin_extensions,
        excluded_bin_files=excluded_bin_files,
        excluded_bin_folders=excluded_bin_folders,
        included_bin_extensions=[],
        excluded_bin_paths=excluded_bin_paths,
    )

    filenpas_csproj=set()
    if csproj_xml_tree is None:
        csproj_xml_tree=csproj.xml_tree
    for xml_node in get_build_xml_nodes_csproj(csproj_xml_tree):
        filenpas_csproj.add(os.path.normpath(os.path.join(csproj.direpa_root, urllib.parse.unquote(xml_node.attrib["Include"]))))

    remaining_files=set()
    for filenpa in filenpas_all:
        if os.path.isdir(filenpa):
            filen=os.path.basename(filenpa)
            if filen[0] == "~":
                continue

        if filenpa.lower() not in [filenpa.lower() for filenpa in filenpas_csproj]:
            remaining_files.add(filenpa)

    if remaining_files:
        nodes:set[_Element]=set()
        searched_tags=set()
        for filenpa in sorted(remaining_files):
            web_conf_elem=False
            relpath=urllib.parse.quote(os.path.relpath(filenpa, csproj.direpa_root)).replace("%5C", "\\")
            if os.path.isfile(filenpa):
                filen=os.path.basename(filenpa)
                if re.match(r"^Web\..+\.config$", filen):                
                    web_conf_elem=True
                ext=os.path.splitext(filenpa)[1]
                if ext == ".cs":
                    tag="Compile"
                elif ext == ".pubxml":
                    tag="None"
                else:
                    tag="Content"
            else:
                tag="Folder"

            node = etree.Element(tag, Include="{}".format(relpath))
            if web_conf_elem is True:
                # <Content Include="Web.Proxy.config">
                #     <DependentUpon>Web.config</DependentUpon>
                # </Content>
                child=etree.SubElement(node, "DependentUpon")
                child.text="Web.config"
            nodes.add(node)
            searched_tags.add(tag)

        print("\nAdding Lines to '{}':\n".format(os.path.basename(csproj.filenpa_csproj)))

        for text in sorted([etree.tostring(node).decode() for node in nodes]):
            print(text)

        user_input=input("\nDo you want to continue (Y/n)? ")
        if user_input.lower() == "n":
            print("Operation cancelled")
            sys.exit(1)

        root=csproj_xml_tree.getroot()
        last_item_group=None
        for item_group in root.findall('ItemGroup', namespaces=get_nsmap(root=root)):
            for tag in searched_tags.copy():
                items=item_group.findall(".//{}[@Include]".format(tag), namespaces=get_nsmap(root=root))
                if items:
                    for node in nodes.copy():
                        if node.tag == tag:
                            insert_node(item_group, items, node)
                            nodes.remove(node)
                    searched_tags.remove(tag)
                    break
            
            last_item_group=item_group
            if not searched_tags:
                break

        pnode_index=None

        for tag in searched_tags.copy():
            if pnode_index is None:
                if last_item_group is not None:
                    parent=last_item_group.getparent()
                    if parent is not None:
                        pnode_index=parent.index(last_item_group)+1
            pnode = etree.Element("ItemGroup")
            if pnode_index is not None:
                root.insert(pnode_index, pnode)
                pnode_index+=1
            for node in nodes.copy():
                if node.tag == tag:
                    insert_node(pnode, list(pnode), node)
                    nodes.remove(node)
            searched_tags.remove(tag)
        
        csproj.write(xml_tree=csproj_xml_tree)
        return True
    else:
        if csproj.debug is True:
            print("No Paths to add to '{}'".format(os.path.basename(csproj.filenpa_csproj)))
        return False

def insert_node(pnode:_Element, siblings:list[_Element], node:_Element):
    index:int
    found_index=False
    for sibling in siblings:
        index=pnode.index(sibling)
        if str(node.attrib["Include"]) < str(sibling.attrib["Include"]):
            found_index=True
            break

    if len(siblings) == 0:
        index=0
    else:
        if found_index is False:
            index+=1

    pnode.insert(index, node)
 