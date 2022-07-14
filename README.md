# Timetable

Print a table showing the committed working hours per day for the specified month

## Legend

1st argument = Year (4 digits)\
2nd argument = Month (Without "0" prefix)\
Optional "weekends" argument" = Show weekends in table

#### Python examples
```
./timemap.py 2022 6
./timemap.py 2022 11 weekends
```
#### Windows examples
```
./timemap_win.exe 2022 6
./timemap_win.exe 2022 11 weekends
```

## Configuration
At the first start, a template configuration file to be compiled will be created in the same folder as the script
```
# Timetable configuration file

[Platform]
platformUrl = platform.example.com

[Worker Credentials]
workerUsername = username
workerPassword = password

[Worker Details]
workerName = NAME SURNAME
workerID = ID

[Settings]
ClearScreenBeforePrinting = True
```
