#/usr/bin/env python3
from copy import deepcopy
from pprint import pprint
import os
import re
import sys
import urllib.parse
from lxml import etree

from .csproj import get_build_xml_nodes_csproj, csproj_update, get_all_build_paths

def csproj_add_files(
    csproj_xml_tree,
    debug,
    direpa_root,
    filenpa_csproj,
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
        "_scripts",
        # "App_Data",
        "Logs",
        "archives",
        "bin",
        "obj",
        "packages",
        "_requests",
        "_db"
    ]
    excluded_bin_files=[
        ".gitignore",
        ".yo-rc.json",
        "files.exclude",
        "hostname_url.txt",
        "log.txt",
    ]
    excluded_bin_extensions=[
        ".csproj",
        ".user",
        ".sln",
        ".log",
        ".csproj_bak"
    ]

    filenpas_all=get_all_build_paths(
        direpa_root=direpa_root,
        excluded_bin_extensions=excluded_bin_extensions,
        excluded_bin_files=excluded_bin_files,
        excluded_bin_folders=excluded_bin_folders,
        included_bin_extensions=[],
    )

    filenpas_csproj=set()
    for xml_node in get_build_xml_nodes_csproj(csproj_xml_tree):
        filenpas_csproj.add(os.path.join(direpa_root, urllib.parse.unquote(xml_node.attrib["Include"])))

    remaining_files=set()
    for filenpa in filenpas_all:
        if os.path.isdir(filenpa):
            filenpa="{}\\".format(filenpa)

        if filenpa.lower() not in [filenpa.lower() for filenpa in filenpas_csproj]:
            pprint(filenpas_csproj)
            remaining_files.add(filenpa)

    if remaining_files:
        nodes=set()
        searched_tags=set()
        for filenpa in sorted(remaining_files):
            web_conf_elem=False
            relpath=urllib.parse.quote(os.path.relpath(filenpa, direpa_root)).replace("%5C", "\\")
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

        print("\nAdding Lines to '{}':\n".format(os.path.basename(filenpa_csproj)))
        for node in nodes:
            etree.dump(node)

        user_input=input("\nDo you want to continue (Y/n)? ")
        if user_input.lower() == "n":
            print("Operation cancelled")
            sys.exit(1)

        root=csproj_xml_tree.getroot()
        last_item_group=None
        for item_group in root.findall('ItemGroup', namespaces=root.nsmap):
            # print(item_group)
            for tag in searched_tags.copy():
                items=item_group.findall(".//{}[@Include]".format(tag), namespaces=root.nsmap)
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
                pnode_index=last_item_group.getparent().index(last_item_group)+1
            pnode = etree.Element("ItemGroup")
            root.insert(pnode_index, pnode)
            pnode_index+=1
            for node in nodes.copy():
                if node.tag == tag:
                    insert_node(pnode, pnode.getchildren(), node)
                    nodes.remove(node)
            searched_tags.remove(tag)
        
        csproj_update(
            csproj_xml_tree,
            direpa_root,
            filenpa_csproj,
        )
        return True
    else:
        if debug is True:
            print("No Paths to add to '{}'".format(os.path.basename(filenpa_csproj)))
        return False

def insert_node(pnode, siblings, node):
    index=None
    found_index=False
    for sibling in siblings:
        index=pnode.index(sibling)
        # print(index)
        if node.attrib["Include"] < sibling.attrib["Include"]:
            found_index=True
            break

    if siblings:
        if found_index is False:
            index+=1
    else:
        index=0

    pnode.insert(index, node)
 