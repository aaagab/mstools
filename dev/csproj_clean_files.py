#/usr/bin/env python3
from pprint import pprint
import os
import re
import sys
import urllib.parse
from lxml import etree, objectify

from .csproj import get_build_xml_nodes_csproj, csproj_update, get_xml_str_without_namespace

def csproj_clean_files(
    csproj_xml_tree,
    debug,
    direpa_root,
    filenpa_csproj,
):
    xml_nodes=get_build_xml_nodes_csproj(csproj_xml_tree)

    remove_nodes=[]
    for xml_node in xml_nodes:
        path_elem=os.path.join(direpa_root, urllib.parse.unquote(xml_node.attrib["Include"]))
        if not os.path.exists(path_elem):
            remove_nodes.append(xml_node)

    if remove_nodes:
        print("\nRemoving Lines to '{}':\n".format(os.path.basename(filenpa_csproj)))
        for node in remove_nodes:
            print(get_xml_str_without_namespace(csproj_xml_tree, node))

        user_input=input("\nDo you want to continue (Y/n)? ")
        if user_input.lower() == "n":
            print("Operation cancelled")
            sys.exit(1)

        for node in remove_nodes.copy():
            node.getparent().remove(node)

        csproj_update(
            csproj_xml_tree,
            direpa_root,
            filenpa_csproj,
        )
        return True
    else:
        if debug is True:
            print("No Paths to clean for '{}'".format(os.path.basename(filenpa_csproj)))
        return False

