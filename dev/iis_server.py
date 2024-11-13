#!/usr/bin/env python3
from pprint import pprint
import json
import os
import signal
import sys
import platform
import shutil
import subprocess
import psutil

launch_pid="{launch_pid}"
project_name="{project_name}"
filenpa_mstools=r"{filenpa_mstools}"
# direpa_sources=r"{direpa_sources}"
dy_wapp=dict({{
    project_name: dict(
        pids=[],
    )
}})

pids=[]
ppid=os.getppid()
pids.append(ppid)

if os.path.exists(filenpa_mstools):
    try:
        with open(filenpa_mstools, "r") as f:
            dy_wapp=json.load(f)
            if project_name not in dy_wapp:
                dy_wapp[project_name]=dict(
                    pids=[ppid],
                )
    except json.decoder.JSONDecodeError:
        dy_wapp[project_name]=dict(
            pids=[ppid],
        )
    
if ppid not in dy_wapp[project_name]["pids"]:
    dy_wapp[project_name]["pids"].insert(0, ppid)

with open(filenpa_mstools, "w") as f:
    f.write(json.dumps(dy_wapp, indent=4, sort_keys=True))


try:
    # os.chdir(direpa_sources)
    cmd=[
        r"C:\Program Files\IIS Express\iisexpress.exe",
        r"/config:{filenpa_config}",
        r"/site:{project_name}",
        # r"/path:{direpa_sources}"
    ]
    print(" ".join(cmd))
    proc=subprocess.Popen(cmd)
    pids.append(proc.pid)
    dy_wapp[project_name]["pids"].insert(0, proc.pid)
    with open(filenpa_mstools, "w") as f:
        f.write(json.dumps(dy_wapp, indent=4, sort_keys=True))
    proc.communicate()
    if proc.returncode != 0:
        sys.exit(1)
except BaseException as e:
    os.kill(int(launch_pid), signal.SIGTERM)
    input("Press any key to continue . . .")
    raise
finally:
    os.remove(os.path.realpath(__file__))
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
