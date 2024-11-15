#!/usr/bin/env python3
from pprint import pprint
import os
import sys
from .csproj import Csproj
from .windows import Windows
import signal
import json
import subprocess
import tempfile
import time

from ..gpkgs import shell_helpers as shell
from ..gpkgs import message as msg

def get_port_pid(port):
    result=shell.cmd_get_value("netstat -ano | findstr :{}".format(port))
    if result is None:
        return None
    else:
        result=int(result.split()[-1])
        if result == 0:
            return None
        else:
            return result
        
def execute_script(
    script_name, 
    window_name,
    dy_vars:dict|None=None,
):
    filenpa_info=os.path.join(os.path.dirname(os.path.realpath(__file__)), script_name)

    with open(filenpa_info, "r") as f:
        data_str=f.read()
        if dy_vars is not None:
            tmp_dy_vars=dict()
            for key, value in dy_vars.items():
                tmp_dy_vars[key]=value
            data_str=data_str.format(**tmp_dy_vars)
   
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write("{}\n".format(data_str).encode())
            proc=subprocess.Popen([
                "start",
                "cmd",
                "/k",
                "title {} & python {}".format( window_name, tmp.name)
            ], shell=True)

            proc.communicate()
            if proc.returncode != 0:
                sys.exit(1)


def iis(
    http_port: int|None, 
    https_port: int|None, 
    bind: str|None,
    reset: bool,
    project_name: str,
    direpa_sources: str,
    filenpa_hostname: str,
):
    win_id=None
    obj_windows=Windows()
    win_id=obj_windows.get_active()

    if http_port is None:
        http_port=9000

    if https_port is None:
        https_port=44300

    if https_port < 44300 or https_port > 44399: # type: ignore
        msg.error("https port must be between 44300 and 44399")
        sys.exit(1)

    filenpa_host_config_src=os.path.join(os.path.expanduser("~"), "Documents", "IISExpress", "config", "applicationhost.config")
    filenpa_host_config_dst=os.path.join(os.path.expanduser("~"), "fty", "tmp", f"mstools-{project_name}-applicationhost.config")
    with open(filenpa_hostname, "w") as f:
        if bind is None:
            f.write(f"https://localhost:{https_port}\n")
        else:
            f.write(f"https://{bind}:{https_port}\n")

        lines=[]
        with open(filenpa_host_config_src, "r") as f:
            append=True
            prefix="            "
            for line in f.read().splitlines():
                if line.strip() == "<sites>":
                    lines.append(line)
                    append=False
                elif line.strip() == "<siteDefaults>":
                    lines.append(rf'{prefix}<site name="{project_name}" id="1" serverAutoStart="true">')
                    lines.append(rf'{prefix}    <application path="/">')
                    lines.append(rf'{prefix}        <virtualDirectory path="/" physicalPath="{direpa_sources}" />')
                    lines.append(rf'{prefix}    </application>')
                    lines.append(rf'{prefix}    <bindings>')
                    lines.append(rf'{prefix}        <binding protocol="http" bindingInformation=":{http_port}:localhost" />')
                    if bind is None:
                        lines.append(rf'{prefix}        <binding protocol="https" bindingInformation=":{https_port}:localhost" />')
                    else:
                        lines.append(rf'{prefix}        <binding protocol="https" bindingInformation="{bind}:{https_port}:" />')
                    lines.append(rf'{prefix}    </bindings>')
                    lines.append(rf'{prefix}</site>')
                    append=True
                elif line.strip() == '<section name="caching" overrideModeDefault="Allow" />':
                    lines.append(rf'{prefix}<section name="caching" overrideModeDefault="Deny" />')
                    continue
                elif line.strip() == '<caching enabled="true" enableKernelCache="true">':
                    lines.append(rf'        <caching enabled="false" enableKernelCache="false">')
                    continue
                if append is True:
                    lines.append(line)

        with open(filenpa_host_config_dst, "w") as f:
            f.write("\n".join(lines)+"\n")

    window_name="client_{}".format(project_name)
    filenpa_mstools=os.path.join(os.path.expanduser("~"), "fty", "tmp", "mstools-{}.json".format(http_port))
    port_pid=get_port_pid(http_port)

    process_cmd=False
    if port_pid is None:
        process_cmd=True
    else:
        if reset is True:
            process_cmd=True
        else:
            process_cmd=False
            msg.info("frontend is already started.")

    if process_cmd is True:
        dy_wapp=dict({
            project_name: dict(
                pids=[],
            )
        })
        try:
            if os.path.exists(filenpa_mstools):
                with open(filenpa_mstools, "r") as f:
                    dy_wapp=json.load(f)
                    if project_name in dy_wapp:
                        if "pids" in dy_wapp[project_name]:
                            for pid in dy_wapp[project_name]["pids"]:
                                try:
                                    os.kill(pid, signal.SIGTERM)
                                except OSError:
                                    pass
        except json.decoder.JSONDecodeError:
            pass

        dy_wapp[project_name]["pids"]=[]

        with open(filenpa_mstools, "w") as f:
            f.write(json.dumps(dy_wapp, indent=4, sort_keys=True))

        execute_script(
            "iis_server.py", 
            window_name=window_name, 
            dy_vars=dict(
                filenpa_mstools=filenpa_mstools,
                filenpa_config=filenpa_host_config_dst,
                project_name=project_name,
                launch_pid=os.getpid(),
            ),
        )

        try:
            while True:
                port_pid=get_port_pid(http_port)
                if port_pid is not None:
                    with open(filenpa_mstools, "r") as f:
                        dy_wapp=json.load(f)
                        if len(dy_wapp[project_name]["pids"]) >= 2:
                            obj_windows.rename(dy_wapp[project_name]["pids"][1], window_name)
                    msg.success("frontend development server started on port '{}' and '{}'".format(http_port, https_port))
                    break
                time.sleep(.3)
        except KeyboardInterrupt:
            sys.exit(1)

        obj_windows.focus(win_id)