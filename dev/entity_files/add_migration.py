#!/usr/bin/env python3
# author: Gabriel Auger
# version: 0.1.0
# name: release
# license: MIT

import json
from pprint import pprint
import os
import re
# import readline
import subprocess
import sys
# from xml.etree import ElementTree
# from lxml.etree import 
from lxml import etree


from ..csproj import csproj_update

def add_migration_csproj(
    direpa_root,
    csproj_xml_tree,
    filenpa_csproj,
    filer,
):
    root=csproj_xml_tree.getroot()
    
    cnodes_siblings_compile=[]
    pnode_compile=None
    pnode_sibling_compile=None

    cnodes_siblings_embed=[]
    pnode_embed=None
    pnode_sibling_embed=None
    
    for item_group in root.findall('ItemGroup', namespaces=root.nsmap):

        if pnode_sibling_compile is None:
            pnode_sibling_compile=item_group
        
        if pnode_compile is None:
            compiles=item_group.findall("Compile", namespaces=root.nsmap)
            if compiles:
                pnode_compile=item_group
                cnodes_siblings_compile=[ item for item in item_group.findall('.//Compile[@Include]', namespaces=root.nsmap) if re.match(r"Migrations\\.*?\.[dD]esigner.cs", item.attrib["Include"])]

        pnode_sibling_embed=item_group

        if pnode_embed is None:
            embeds=item_group.findall("EmbeddedResource", namespaces=root.nsmap)
            if embeds:
                pnode_embed=item_group
                cnodes_siblings_embed=[ item for item in item_group.findall('.//EmbeddedResource[@Include]', namespaces=root.nsmap) if re.match(r"Migrations\\.*?\.resx", item.attrib["Include"])]
  
    # pnode_compile=None
    for ntype in ["compile", "embed"]:
        pnode=None
        pnode_sibling=None
        cnodes_siblings=None

        if ntype == "compile":
            pnode=pnode_compile
            pnode_sibling=pnode_sibling_compile
            cnodes_siblings=cnodes_siblings_compile
        elif ntype == "embed":
            pnode=pnode_embed
            pnode_sibling=pnode_sibling_embed
            cnodes_siblings=cnodes_siblings_embed

        if pnode is None:
            pnode = etree.Element("ItemGroup")
            if pnode_sibling is None:
                print("This shouldn't happen unless csproj does not have ItemGroup")
                sys.exit(1)
            pnode_sibling_index=list(root.getchildren()).index(pnode_sibling)
            root.insert(pnode_sibling_index+1, pnode)

        cnode_sibling_index=None
        if cnodes_siblings == []:
            cnode_sibling_index=len(pnode.getchildren())
        else:
            cnode_sibling_index=pnode.getchildren().index(cnodes_siblings[-1])

        next_index=cnode_sibling_index+1

        node=None
        if ntype == "compile":
            # <ItemGroup>
            #     <Compile Include="Migrations\202004061322259_InitialCreate.cs" />
            #     <Compile Include="Migrations\202004061322259_InitialCreate.Designer.cs">
            #         <DependentUpon>202004061322259_InitialCreate.cs</DependentUpon>
            #     </Compile>
            # </ItemGroup>
            node = etree.Element("Compile", Include="Migrations\{}.cs".format(filer))
            pnode.insert(next_index, node)
            next_index+=1
            node = etree.Element("Compile", Include="Migrations\{}.Designer.cs".format(filer))
        elif ntype == "embed":
            # <ItemGroup>
            #     <EmbeddedResource Include="Migrations\202004061322259_InitialCreate.resx">
            #       <DependentUpon>202004061322259_InitialCreate.cs</DependentUpon>
            #     </EmbeddedResource>
            # </ItemGroup>
            node = etree.Element("EmbeddedResource", Include="Migrations\{}.resx".format(filer))

        etree.SubElement(node, "DependentUpon").text = "{}.cs".format(filer)
        pnode.insert(next_index, node)

    csproj_update(
        csproj_xml_tree,
        direpa_root,
        filenpa_csproj,
    )