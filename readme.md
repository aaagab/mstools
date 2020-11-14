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