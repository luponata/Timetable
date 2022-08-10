# Timetable

Print a table showing the committed working hours per day for the specified month

## Legend

1° parameter = Year (4 digits)\
2° parameter = Month (1/2 digits, Without "0" prefix)\
Optional "weekends" parameter" = Show weekends in table\
You can call Timetable without parameters to see current month hours

#### Examples
```
timemap.[py/exe] (use current month)
timemap.[py/exe] weekends (use current month plus weekends)
timemap.[py/exe] 2022 6 (specifies year and month)
timemap.[py/exe] 2022 11 weekends (specifies year and month plus weekends)
```
## Configuration
At the first start, a template configuration file to be customized will be created in the same folder as the script:
```
# Timetable configuration file

[Platform]
Platform Url = platform.example.com

[Worker Credentials]
Worker Username = USERNAME
Worker Password = PASSWORD

[Worker Details]
Worker Name = NAME SURNAME
Worker ID = ID

[Settings]
Clear screen before printing = True
```
After the first launch, the credentials on the configuration file will be deleted, hashed and saved on a hidden JSON file, to update them, just put the newer ones on the configuration file again.
