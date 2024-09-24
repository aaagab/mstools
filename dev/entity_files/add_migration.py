#!/usr/bin/env python3
from pprint import pprint
import re
import sys
from lxml.etree import _Element
from lxml import etree


from ..csproj import get_nsmap, Csproj

def add_migration_csproj(
    csproj:Csproj,
    filer:str,
):
    root=csproj.xml_tree.getroot()
    
    cnodes_siblings_compile:list[_Element]=[]
    pnode_compile:_Element|None=None
    pnode_sibling_compile:_Element|None=None

    cnodes_siblings_embed=[]
    pnode_embed=None
    pnode_sibling_embed=None

    nsmap=get_nsmap(root)
    
    for item_group in root.findall('ItemGroup', namespaces=nsmap):

        if pnode_sibling_compile is None:
            pnode_sibling_compile=item_group
        
        if pnode_compile is None:
            compiles=item_group.findall("Compile", namespaces=nsmap)
            if compiles:
                pnode_compile=item_group
                cnodes_siblings_compile=[ item for item in item_group.findall('.//Compile[@Include]', namespaces=nsmap) if re.match(r"Migrations\\.*?\.[dD]esigner.cs", str(item.attrib["Include"]))]

        pnode_sibling_embed=item_group

        if pnode_embed is None:
            embeds=item_group.findall("EmbeddedResource", namespaces=nsmap)
            if embeds:
                pnode_embed=item_group
                cnodes_siblings_embed=[ item for item in item_group.findall('.//EmbeddedResource[@Include]', namespaces=nsmap) if re.match(r"Migrations\\.*?\.resx", str(item.attrib["Include"]))]
  
    for ntype in ["compile", "embed"]:
        pnode:_Element|None=None
        pnode_sibling:_Element|None=None
        cnodes_siblings:list[_Element]=[]

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
            pnode_sibling_index=list(root).index(pnode_sibling)
            root.insert(pnode_sibling_index+1, pnode)

        cnode_sibling_index=None
        if len(cnodes_siblings) == 0:
            cnode_sibling_index=len(list(pnode))
        else:
            cnode_sibling_index=list(pnode).index(cnodes_siblings[-1])

        next_index=cnode_sibling_index+1

        node:_Element
        if ntype == "compile":
            # <ItemGroup>
            #     <Compile Include="Migrations\202004061322259_InitialCreate.cs" />
            #     <Compile Include="Migrations\202004061322259_InitialCreate.Designer.cs">
            #         <DependentUpon>202004061322259_InitialCreate.cs</DependentUpon>
            #     </Compile>
            # </ItemGroup>
            node = etree.Element("Compile", Include=r"Migrations\{}.cs".format(filer))
            pnode.insert(next_index, node)
            next_index+=1
            node = etree.Element("Compile", Include=r"Migrations\{}.Designer.cs".format(filer))
        elif ntype == "embed":
            # <ItemGroup>
            #     <EmbeddedResource Include="Migrations\202004061322259_InitialCreate.resx">
            #       <DependentUpon>202004061322259_InitialCreate.cs</DependentUpon>
            #     </EmbeddedResource>
            # </ItemGroup>
            node = etree.Element("EmbeddedResource", Include=r"Migrations\{}.resx".format(filer))

        etree.SubElement(node, "DependentUpon").text = "{}.cs".format(filer)
        pnode.insert(next_index, node)

    csproj.write(csproj.xml_tree)