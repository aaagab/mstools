#!/usr/bin/env python3
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
    port: int|None, 
    reset: bool,
    project_name: str,
    direpa_sources: str,
    filenpa_hostname: str,
):
    win_id=None
    if port is None:
        port=9000

    obj_windows=Windows()
    win_id=obj_windows.get_active()

    window_name="client_{}".format(project_name)
    filenpa_mstools=os.path.join(os.path.expanduser("~"), "fty", "tmp", "mstools-{}.json".format(port))

    with open(filenpa_hostname, "w") as f:
        f.write(f"http://localhost:{port}\n")

    port_pid=get_port_pid(port)

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
                project_name=project_name,
                direpa_sources=direpa_sources,
                port=port,
                launch_pid=os.getpid(),
            ),
        )

        try:
            while True:
                port_pid=get_port_pid(port)
                if port_pid is not None:
                    with open(filenpa_mstools, "r") as f:
                        dy_wapp=json.load(f)
                        if len(dy_wapp[project_name]["pids"]) >= 2:
                            obj_windows.rename(dy_wapp[project_name]["pids"][1], window_name)
                    msg.success("frontend development server started on port '{}'".format(port))
                    break
                time.sleep(.3)
        except KeyboardInterrupt:
            sys.exit(1)

        obj_windows.focus(win_id)