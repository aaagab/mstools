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

for -filemask */Logs/ will match all the logs folder even the nested one and you don't want that. You have to provide full path and the full path must come from source and not from destination.
"" I believe the problem is it also check on src and dst so for instance  
Exclusions:  
- in order to exclude a folder that is in source, and not in dst. Then use absolute path from src in filemask
- in order to exclude a folder that is not in source, Then use absolute path from dst in filemask
- if folder in src and folder in dst (for instance logs) but you don't want to synchronize that folder at all you need to add both absolute src and absolute dst. The subtulties is that if dir is present on dst only and excluded on dst it is then ignored and not erased but if it exists also in src but excluded on dst then it is still synchronized, only that it is not deleted first so it means that any existing files on dst is not going to be erased or overwritten if they don't exist on src. However src is still going to synchronize folder with dst. so folder needs to be excluded on both src and dst in the case the folder needs to be ignored on dst. User put generally */logs so it ignores in both dst and src, however */logs also ignore any nested folders and user may not want that. So the only solution for folder to ignore at dst is to also ignore them at src. If you want to ignore absolute path, then you have exclude both src and dst in filemask. Otherwise if you only exclude absolute in src and it exists in dst, then it is deleted from dst.
- Folder should always ends with forward slash in filemask. Files can also be included, and same story they have to be both puth in filemask absolute with src and dst. For instance if a folder is just included from source then it is always synchronize on destination even when not needed.
- I was not able to make absolute path working with include in filemask, ""I believe I am able to make the exclude work but now I am even doubting that. Apparently include for directory only work with first children directories, as soon as you nest, winscp just ignore your filemask.

With option -delete filemask filter for folder to exclude must be exclude the same folders from remote but also from local otherwise folders are deleted on remote if only remote is put.

# https://stackoverflow.com/questions/19566820/how-to-deploy-project-with-msdeploy-instead-of-msbuild
# C:\Program Files\IIS\Microsoft Web Deploy V3\msdeploy.exe
# C:\Program Files (x86)\IIS\Microsoft Web Deploy V3\msdeploy.exe


%userprofile%\fty\etc\mstools\settings.json
```json
{
    "apps": [
        {
            "direl": "e/example",
            "name": "appname1",
            "port": 9020
        }
    ],
    "direpa_framework": "C:\\Program Files (x86)\\Reference Assemblies\\Microsoft\\Framework\\.NETFramework",
    "filenpa_csc": "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community\\MSBuild\\Current\\Bin\\Roslyn\\csc.exe",
    "filenpa_express": "C:\\Program Files (x86)\\IIS Express\\iisexpress.exe",
    "filenpa_msbuild": "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community\\MSBuild\\Current\\Bin\\msbuild.exe",
    "filenpa_msdeploy": "C:\\Program Files (x86)\\IIS\\Microsoft Web Deploy V3\\msdeploy.exe",
    "profiles": [
        {
            "direpa_deploy": "C:\\Users\\user\\fty\\local",
            "hostname": "http://localhost",
            "name": "debug"
        }
    ]
}
```

for publish profiles there is an option to synchronize (mirror) files from sources to build: `/p:DeleteExistingFiles=True`  
Odly that option does not work for folder in publish directory. So there is no way to automatically remove them, it has to be done manually.   

msdeploy with args -skip:objectName=dirPath,absolutePath={} only accept an absolute path to be accurate. If a relative path is given then any relative path that matches the path is going to be affected. For instance a \\log path would skip all \\log folders in the project. If full path can't be provided at least provide root folders for instance /e/example/log . For a web application on azure pipeline release the path is the web application path not the physical internal path. For instance the full path would be domain.com/e/example/App_Data

## iisexpress
`mstools --build --iis --reset --bind 192.168.1.30`  

Issue:
  Failed to register URL "https://192.168.1.30:44300/" for site "example" application "/". Error description: Access is denied. (0x80070005)
Fix:
  open cmd in administrator mode
  netsh http add urlacl url=https://192.168.1.30:44300/ user=everyone

  remove rule if not needed anymore:
  netsh http delete urlacl url=https://192.168.1.30:44300/

Issue:
  Can't connect from external computer on url https://192.168.1.30:44300
  The connection has timed out
Fix:
netsh advfirewall firewall add rule name="IISExpressWeb" dir=in protocol=tcp localport=44300 profile=private remoteip=localsubnet action=allow

