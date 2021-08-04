#!/usr/bin/env python3
import json
from pprint import pprint
import os
import re
import subprocess
import sys
from lxml import etree

from ..csproj import csproj_update, get_xml_str_without_namespace

def clean_migrations(
    csproj_xml_tree,
    current_migrations,
    direpa_migrations,    
    direpa_root,
    filenpa_csproj,
    force=False,
):
    need_cleaning=False
    filenpas_migrations={}
    for elem in os.listdir(direpa_migrations):
        reg_migration_file=re.match(r"^(?P<date>[0-9]{15})_(?P<filer>.*?)\.(?P<ext>(?:cs|Designer\.cs|resx))$",elem)
        if reg_migration_file:
            date=reg_migration_file.group("date")
            filer=reg_migration_file.group("filer")
            ext=reg_migration_file.group("ext")
            if not date in filenpas_migrations:
                filenpas_migrations[date]={}
                filenpas_migrations[date]["_filens"]=[]

            if not filer in filenpas_migrations[date]:
                filenpas_migrations[date][filer]=[]

            filenpas_migrations[date][filer].append(ext)
            filenpas_migrations[date]["_filens"].append(elem)

    todelete_migrations={}
    for date in filenpas_migrations:
        for filen in filenpas_migrations[date]:
            if filen != "_filens":
                if not(date in current_migrations and filen in current_migrations[date]):
                    if not date in todelete_migrations:
                        todelete_migrations[date]={}
                    todelete_migrations[date]["_filens"]=filenpas_migrations[date]["_filens"]

    deleted_migrations=[]
    kept_migrations=[]
    for date in todelete_migrations:
        if need_cleaning is False:
            need_cleaning=True

        filens=todelete_migrations[date]["_filens"]
        migration_name=filens[0].split(".")[0]
        user_input=input("\nDo you want to clean migration '{}' [Y/n]? ".format(migration_name))
        if user_input.lower() == "n":
            print("Migration kept '{}'".format(migration_name))
            kept_migrations.append(date)
        else:
            deleted_migrations.append(date)
            print("\nRemoving Files:")
            print("{}".format("\n".join(filens)))
            for filen in filens:
                filenpa=os.path.join(direpa_migrations, filen)
                os.remove(filenpa)

    # <ItemGroup>
    #     <Compile Include="Migrations\202004061322259_InitialCreate.cs" />
    #     <Compile Include="Migrations\202004061322259_InitialCreate.Designer.cs">
    #         <DependentUpon>202004061322259_InitialCreate.cs</DependentUpon>
    #     </Compile>
    # </ItemGroup>

    # <ItemGroup>
    #     <EmbeddedResource Include="Migrations\202004061322259_InitialCreate.resx">
    #       <DependentUpon>202004061322259_InitialCreate.cs</DependentUpon>
    #     </EmbeddedResource>
    # </ItemGroup>
    root=csproj_xml_tree.getroot()
    ns=dict(ns=format(root.nsmap[None]))
    csproj_xml_elems=root.xpath('.//ns:*[contains(@Include, "Migrations\\")]', namespaces=ns)
    todelete_xml_elems={}
    for xml_elem in csproj_xml_elems:
        attr=xml_elem.attrib["Include"]
        date=attr.replace("Migrations\\", "").split("_")[0]
        if re.match(r"^[0-9]{15}$", date):
            if date not in current_migrations:
                if date not in todelete_xml_elems:
                    todelete_xml_elems[date]=[]
                todelete_xml_elems[date].append(xml_elem)

    xml_elems_removed=False
    for date in todelete_xml_elems:
        if need_cleaning is False:
            need_cleaning=True

        if date not in kept_migrations:
            print()
            for xml_elem in todelete_xml_elems[date]:
                print(get_xml_str_without_namespace(csproj_xml_tree, xml_elem))
            if date in deleted_migrations:
                xml_elems_removed=True
                removing_nodes(filenpa_csproj, todelete_xml_elems[date])
            else:
                user_input=input("Do you want to remove unused entries from '{}' [Y/n]? ".format(os.path.basename(filenpa_csproj)))
                if user_input.lower() == "n":
                    print("Migration kept '{}'".format(migration_name))
                else:
                    xml_elems_removed=True
                    removing_nodes(filenpa_csproj, todelete_xml_elems[date])

    if xml_elems_removed is True:
        csproj_update(
            csproj_xml_tree,
            direpa_root,
            filenpa_csproj,
            force=force,
        )

    if need_cleaning is False:
        print("Cleaning not needed")

def removing_nodes(filenpa_csproj, xml_elems):
    print("Removing Entries from '{}'\n".format(os.path.basename(filenpa_csproj)))
    for xml_elem in xml_elems:
        xml_elem.getparent().remove(xml_elem)
