#!/usr/bin/env python3
from datetime import datetime
import json
from pprint import pprint
import os
import re
import shlex
import subprocess
import sys
from lxml import etree

from .csproj_update import build_project
from .entity_files.add_migration import add_migration_csproj
from .entity_files.clean_migrations import clean_migrations

from ..gpkgs import message as msg

def entity(
    csproj_xml_tree,
    direpa_root,
    debug,
    filenpa_assembly,
    filenpa_csproj,
    filenpa_msbuild,
    params,
    xml_root_namespace,
):
    if params is None:
        print("## Examples:")
        with open(r"A:\wrk\d\doc\aspnet\entity\all_examples.txt", "r") as f:
            for line in f.read().splitlines():
                print(line)

        print()
        print()
        msg.info("""
            ## Nuget Package Manager Commands:
                _ Add-Migration InitialCreate
                _ Update-Database
                _ Add-Migration AddColumn
                _ Update-Database
                _ Add-Migration AddAnotherColumn
                _ Update-Database
                _ Update-Database -TargetMigration InitialCreate
                _ Update-Database -TargetMigration InitialCreate -Script
                _ Update-Database -SourceMigration AddColumn -TargetMigration AddAnotherColumn
                _ Get-Migrations
                _ Enable-Migrations
            
            ## Custom Commands:
                _ Clean-Migrations
                    This command clean not used migration
                    it lists all migrations.
                    it gets the one that are not part of the current.
                    it get a diff in a sql statement and save the difference in a sql file.
                    then it saves everything in a rollback folder.
                    It deletes the migrations files.
                    Delete just remove migration files that are not part of Get-Migrations and it clean csproj from them.
                    To rollback a migration you need to use Update-Database 
                _ Raw
                    After this argument add any command for the entity command line tool
        """, heredoc=True, indent="  ", bullet="")
        sys.exit(0)
    else:
        migration_name=r"[a-zA-Z0-9-_\.]*"
        flags=r"(?P<flags>.*)"
        regs=[
            r"^Add-Migration\s+(?P<name>{}){}$".format(migration_name, flags),
            r"^Clean-Migrations$",
            r"^Enable-Migrations{}$".format(flags),
            r"^Get-Migrations$",
            r"^Update-Database\s-SourceMigration\s+(?P<source>{})\s-TargetMigration\s+(?P<target>{}){}$".format(migration_name, migration_name, flags),
            r"^Update-Database\s-TargetMigration\s+(?P<target>{}){}$".format(migration_name, flags),
            r"^Update-Database{}$".format(flags),
            r"Raw(?P<cmd>.*)",
            # r"^Update-Database\s-TargetMigration\s+(?P<target_name>{})\s+-Script$".format(migration_name),
        ]

        user_cmd=params.strip()
        reg_found=False
        dy_params=dict()
        for reg in regs:
            reg_db=re.match(reg, user_cmd)
            if reg_db:
                reg_found=True
                dy_params=reg_db.groupdict()
                break
        
        known_flags=[
            "-Force",
            "-IgnoreChanges",
            "-Script",
            "-Verbose",
            "--show",
        ]

        if reg_found is False:
            msg.error("""
                commad: '{}'
                does not match any of the following regex:
                {}

                {} 
            """.format(
                user_cmd,
                "    \n".join(regs),
                "    \n".join(known_flags),                
            ), heredoc=True, exit=1)

        flags=[]
        if "flags" in dy_params:
            flags=shlex.split(dy_params["flags"].strip())

        params=shlex.split(params)
        main_cmd=params[0]

        for flag in flags:
            if flag not in known_flags:
                msg.error("For cmd '{}' Flag unknown '{}' from the list '{}'".format(main_cmd, flag, known_flags), exit=1 )

        commons=[
            # "verbose",
            "no-color",
            # "prefix-output",
            "assembly",
            "project-dir",
            "language",
            "data-dir",
            "root-namespace",
            "config"
        ]
        direpa_migrations=os.path.join(direpa_root, "Migrations")
        cmd=[get_entity_path(direpa_root)]

        if main_cmd == "Raw":
            options=shlex.split(dy_params["cmd"].strip())
            cmd.extend(options)
            subprocess.run(cmd)
            sys.exit(0)
        elif main_cmd in ["Enable-Migrations", "Add-Migration", "Update-Database"]:
            build_project(
                debug,
				direpa_root,
				csproj_xml_tree,
				filenpa_assembly,
				filenpa_csproj,
				filenpa_msbuild,
            )
            options=[]
            export_sql_script=False

            source=None
            target=None
            if main_cmd == "Update-Database":
                cmd.append("database")
                cmd.append("update")
                if "source" in dy_params:
                    export_sql_script=True
                    cmd.append("--source")
                    cmd.append(dy_params["source"])
                if "target" in dy_params:
                    export_sql_script=True
                    cmd.append("--target")
                    cmd.append(dy_params["target"])
                options.append("script")
                options.append("force")
                options.append("verbose")
                if "-Script" in flags:
                    export_sql_script=True
            elif main_cmd == "Enable-Migrations":
                cmd.append("migrations")
                cmd.append("enable")
                options.append("json")
                options.append("force")
            elif main_cmd == "Add-Migration":
                cmd.append("migrations")
                cmd.append("add")
                cmd.append(dy_params["name"])
                options.append("json")
                options.append("force")
                options.append("ignore-changes")

            cmd.extend(get_options(
                commons,
                direpa_root,
                filenpa_assembly,
                flags, 
                options,
                xml_root_namespace,
            ))
            cmd_string=get_cmd_str(cmd)
            print("\n{}\n".format(cmd_string))

            if "--show" not in flags:
                process=subprocess.Popen(cmd, bufsize=1, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                add_migration_filer=None
                sql_statements=[]

                rescaffolding=False
                for line in iter(process.stdout.readline, ''):
                    print(line, end="")
                    if main_cmd == "Add-Migration":
                        if re.match(r"^Re-scaffolding migration .*$", line):
                            rescaffolding=True

                        if add_migration_filer is None and rescaffolding is False:
                            reg_migration=re.match(r"^\s+\"migration\":\s.+Migrations\\\\(?P<filer>[0-9]{15}_.+?)\..+$",line)
                            if reg_migration:
                                add_migration_filer=reg_migration.group("filer")
                    elif main_cmd == "Update-Database" and "-Script" in flags:
                        sql_statements.append(line)
                    
                    sys.stdout.flush()
                process.wait()
                errcode = process.returncode

                if add_migration_filer is not None:
                    add_migration_csproj(
                        direpa_root,
                        csproj_xml_tree,
                        filenpa_csproj,
                        add_migration_filer,
                    )
                elif len(sql_statements) > 0:
                    direpa_sql=os.path.join(direpa_root, "_migrations_sql")
                    if not os.path.exists(direpa_sql):
                        os.makedirs(direpa_sql)

                    filen_sql="{:%Y%m%d%H%M%S}_".format(datetime.now())
                    if source is not None:
                        filen_sql+="_from_{}".format(source).lower()
                    if target is not None:
                        filen_sql+="_to_{}".format(target).lower()
                    filen_sql+=".sql"
                    filenpa_sql=os.path.join(direpa_sql, filen_sql)
                    with open(filenpa_sql, "w") as f:
                        f.write("".join(sql_statements))
                    print("sql exported to '{}'".format(filenpa_sql))
                    validate_sql(filenpa_sql)

        elif main_cmd == "Get-Migrations":
            build_project(
                debug,
				direpa_root,
				csproj_xml_tree,
				filenpa_assembly,
				filenpa_csproj,
				filenpa_msbuild,
            )
            print()
            get_current_migrations(
                commons,
                cmd,
                direpa_root,
                filenpa_assembly,
                xml_root_namespace,
                show=True,
            )
            sys.exit(0)
        elif main_cmd == "Clean-Migrations":
            current_migrations=get_current_migrations(
                commons,
                cmd,
                direpa_root,
                filenpa_assembly,
                xml_root_namespace,
            )

            # current_migrations={'202004131322160': 'TestField', '202004061322259': 'InitialCreate', '202001291917567': 'AutomaticMigration'}
            clean_migrations(
                csproj_xml_tree,
                current_migrations,
                direpa_migrations,    
                direpa_root,
                filenpa_csproj,
            )
        else:
            print("Unknown Parameter '{}'".format(main_cmd))
            sys.exit(1)
        
def get_cmd_str(cmd):
    cmd_string=""
    for e, elem in enumerate(cmd):
        if " " in elem:
            elem='"{}"'.format(elem)
        if e == 0:
            cmd_string=elem
        else:
            cmd_string+=" {}".format(elem)

    return cmd_string

def get_current_migrations(
    commons,
    cmd,
    direpa_root,
    filenpa_assembly,
    xml_root_namespace,
    show=False,
    ):
    # commons, cmd, show=False
    cmd.append("migrations")
    cmd.append("list")
    cmd.extend(get_options(
        commons,
        direpa_root,
        filenpa_assembly,
        [], 
        [],
        xml_root_namespace, 
    ))
    result=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        print("Error cmd:\n{}".format(get_cmd_str(cmd)))
        if result.stderr:
            print(result.stderr.decode())
        if result.stdout:
            print(result.stdout.decode())
        sys.exit(1)
    else:
        current_migrations={}
        for line in result.stdout.decode("utf-8").splitlines():
            reg_migration=re.match(r"^(?P<date>[0-9]{15})_(?P<filer>.*)$",line)
            if reg_migration:
                if show is True:
                    print(line)
                date=reg_migration.group("date")
                filer=reg_migration.group("filer")
                current_migrations[date]=filer

        return current_migrations

def get_options(
    commons,
    direpa_root,
    filenpa_assembly,
    flags, 
    options,
    xml_root_namespace, 
):
    tmp_options=[]

    options.extend(commons)
    for option in options:
        if option == "json":
            tmp_options.append("--{}".format(option))
        elif option == "script":
           if "-Script" in flags:
                tmp_options.append("--{}".format(option))
        elif option == "force":
            if "-Force" in flags:
                tmp_options.append("--{}".format(option))
        elif option == "ignore-changes":
            if "-IgnoreChanges" in flags:
                tmp_options.append("--ignore-changes")
        elif option == "verbose":
            if "-Verbose" in flags:
                tmp_options.append("--{}".format(option))
        elif option == "no-color":
            tmp_options.append("--{}".format(option))
        elif option == "prefix-output":
            tmp_options.append("--{}".format(option))
        elif option == "assembly":
            tmp_options.append("--{}".format(option))
            tmp_options.append("{}".format(filenpa_assembly))
        elif option == "project-dir":
            tmp_options.append("--{}".format(option))
            tmp_options.append("{}".format(direpa_root))
        elif option == "language":
            tmp_options.append("--{}".format(option))
            tmp_options.append("C#")
        elif option == "data-dir":
            tmp_options.append("--{}".format(option))
            tmp_options.append("{}".format( os.path.join(direpa_root, "App_Data")))
        elif option == "root-namespace":
            tmp_options.append("--{}".format(option))
            tmp_options.append("{}".format(xml_root_namespace))
        elif option == "config":
            tmp_options.append("--{}".format(option))
            tmp_options.append("{}".format(os.path.join(direpa_root, "Web.config")))

    return tmp_options

def get_entity_path(
    direpa_root,
):
    direpa_packages=os.path.join(direpa_root, "packages")

    filenpa_entity=None
    for elem in os.listdir(direpa_packages):
        if re.match(r"^EntityFramework\.[0-9]\.[0-9]\.[0-9]$", elem):
            print(elem)
            filenpa_entity=os.path.join(direpa_packages, elem, "tools", "net45", "any", "ef6.exe")
            break

    if filenpa_entity is None:
        print("Entity exe not found in '{}'".format(direpa_packages))
        sys.exit(1)
    elif not os.path.exists(filenpa_entity):
        print("'{}' not found ".format(filenpa_entity))
        sys.exit(1)
    else:
        return filenpa_entity

def validate_sql(filenpa_sql):
    process = subprocess.Popen(["where", "sqlcmd"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = process.communicate()[0]
    if process.returncode == 0:
        returncode=-1
        content=[]
        with open(filenpa_sql, "r") as f:
            content=f.read().splitlines()
            stat="SET PARSEONLY ON;"
            if content[0] != stat:
                content.insert(0,stat)

        starting=True
        while returncode != 0:
            if starting is True:
                starting=False
            else:
                if len(content) > 1:
                    del content[1]
                else:
                    print("File empty '{}'".format(filenpa_sql))
                    break
        
            with open(filenpa_sql, "w") as f:
                f.write("\n".join(content))

            cmd=shlex.split(r'sqlcmd -b -S (localdb)\\MSSQLLocalDB -d webdev -i "{}"'.format(filenpa_sql))
            process=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr=process.communicate()
            returncode=process.returncode
        
        del content[0]
        with open(filenpa_sql, "w") as f:
            f.write("\n".join(content))