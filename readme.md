winscp.com hostname1 /command "synchronize remote -mirror -delete -criteria=time -transfer=automatic -filemask=""| */App_Data/log.txt; */Uploads/; */Logs/"" C:\Users\user\fty\wrk\e\example\1\src\_publish\build /www/e/example" exit

```python
filenpa_tmp=tempfile.TemporaryFile().name
with open(filenpa_tmp, "w") as f:
    f.write("{}\n".format(
        r'synchronize remote -mirror -delete -criteria=time -transfer=automatic -filemask="| */App_Data/log.txt; */Uploads/; */Logs/" "{}" "{}"'.format(
        direpa_publish,
        direpa_ftp_dst,
    )))

cmd=[
    "winscp.com",
    winscp_profile,
    "/script={}".format(filenpa_tmp),
    "exit"
]

process=subprocess.Popen(cmd)
process.communicate()
```

With option -delete filemask filter for folder to exclude must be exclude the same folders from remote but also from local otherwise folders are deleted on remote if only remote is put.


# https://stackoverflow.com/questions/19566820/how-to-deploy-project-with-msdeploy-instead-of-msbuild
# C:\Program Files\IIS\Microsoft Web Deploy V3\msdeploy.exe
# C:\Program Files (x86)\IIS\Microsoft Web Deploy V3\msdeploy.exe


%userprofile%\fty\etc\mstools\settings.json
```json
{
    "apps": {
        "appname1": {
            "port": 9020,
            "direl": "e/example"
        },
        "appname2": {
            "port": 9030,
            "direl": "/e/example"
        }
    },
    "globals": {
        "confs": {
            "debug": {
                "deploy_path": {
                    "hostname1": "{user_profile}/fty/local",
                    "hostname2": "{user_profile}/fty/local"
                },
                "hostname": "http://localhost"
            },
            "dev": {
                "deploy_path": {
                    "hostname1": "V:/",
                    "hostname2": "ftp://hostname1/www"
                },
                "hostname": "https://www.example.com"
            },
            "myprod": {
                "deploy_path": {
                    "hostname1": "V:/",
                    "hostname2": "ftp://hostname1/www"
                },
                "hostname": "https://www.example.com"
            },
            "proxy": {
                "deploy_path": {
                    "hostname1": "{user_profile}/fty/local",
                    "hostname2": "{user_profile}/fty/local"
                },
                "hostname": "https://www.example.com"
            },
            "test": {
                "deploy_path": {
                    "hostname1": "W:/",
                    "hostname2": "ftp://hostname1/www"
                },
                "hostname": "https://www.example.com"
            },
            "prod": {
                "deploy_path": {
                    "hostname1": "{user_profile}/fty/releases",
                    "hostname2": "{user_profile}/fty/releases"
                },
                "hostname": "https://webapps.example.com"
            }
        },
        "direpa_framework": "C:/Program Files (x86)/Reference Assemblies/Microsoft/Framework/.NETFramework",
        "filenpa_express": "C:/Program Files (x86)/IIS Express/iisexpress.exe",
        "filenpa_csc": "C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/MSBuild/Current/Bin/Roslyn/csc.exe",
        "filenpa_msbuild": "C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/MSBuild/Current/Bin/msbuild.exe",
        "filenpa_msdeploy": "C:/Program Files (x86)/IIS/Microsoft Web Deploy V3/msdeploy.exe"
    }
}
```