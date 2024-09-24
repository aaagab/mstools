#/usr/bin/env python3
from pprint import pprint
import os
import re
import sys
import urllib.parse
from lxml.etree import _Element, _ElementTree

from .csproj import get_build_xml_nodes_csproj, get_xml_str_without_namespace, Csproj

def csproj_clean_files(
    csproj:Csproj,
    force:bool=False,
):
    xml_tree=csproj.xml_tree
    xml_nodes=get_build_xml_nodes_csproj(xml_tree)

    remove_nodes:list[_Element]=[]
    for xml_node in xml_nodes:
        path_elem=os.path.join(csproj.direpa_root, urllib.parse.unquote(xml_node.attrib["Include"]))
        if not os.path.exists(path_elem):
            remove_nodes.append(xml_node)

    if remove_nodes:
        print("\nRemoving Lines to '{}':\n".format(os.path.basename(csproj.filenpa_csproj)))
        for node in remove_nodes:
            print(get_xml_str_without_namespace(xml_tree, node))

        if force is False:
            user_input=input("\nDo you want to continue (Y/n)? ")
            if user_input.lower() == "n":
                print("Operation cancelled")
                sys.exit(1)

        for node in remove_nodes.copy():
            parent=node.getparent()
            if parent is not None:
                parent.remove(node)

        csproj.write(xml_tree)
        return True
    else:
        if csproj.debug is True:
            print("No Paths to clean for '{}'".format(os.path.basename(csproj.filenpa_csproj)))
        return False

