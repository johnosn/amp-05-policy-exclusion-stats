[![Gitter chat](https://img.shields.io/badge/gitter-join%20chat-brightgreen.svg)](https://gitter.im/CiscoSecurity/AMP-for-Endpoints "Gitter chat")

### AMP for Endpoints Policy Exclusion Statistics

This script is intended to count the number of exclusions per policy and provide a caution or warning message regarding policies that are near or exceed the maximum number or process exclusion.

### Script Execution Overview

1. Connects to the Cisco AMP for Endpoints API.
2. Enumerates all of the policies in the environment.
3. Downloads a copy of the policy.xml file for each policy and stores it in the "output" "policy_files" folder.
4. Evaluates the exclusions for each policy.
5. Creates tables with the number of file and policy exclusions for each policy.
6. Stores the tables in .csv format to the "output" folder.
7. Generates a Caution and Warning message for policies that have a large number of process exclusions.

### Before Using

You must update the following:

1. Configure the ```.\config\api.cfg```
   1. Modify the amp_client_id
   2. Modify the amp_host if the credentials are not in the North American cloud
2. Create credential in Windows "Credential Manager"
   1. Under "Windows Credentials" click "Add a generic credential".
   2. For "Internet or network address:" enter "AMP".
   3. For "User name:" enter the AMP API client ID
   4. For "Password:" enter the AMP API client secret

## Usage

```cmd
python policy_exclusions_stats.py
```

### File Output

- ***policy_name*.xml:** Policy.xml files are stored as *policy_name*.xml in the ```.\output\policy_files\``` folder.
- **Path_exculsions.csv:** The count of path exclusions by policy name can be found at ```.\output\path_exclusions.csv```.
- **Process_exclusions.csv:** The count of process exclusions by policy name can be found at ```.\output\process_exclusions.csv``` file. This output file includes the number of process exclusions that apply to all child processes which is not included in the screen output.

### Example Script Screen Output

``+--------------------------------------------+--------+------------------+------------+--------------------+``  
``| Policy Name                                |   Path |   File Extension |   Wildcard |   Total Exclusions |``  
``|--------------------------------------------+--------+------------------+------------+--------------------|``  
``| Built-In Mac                               |      6 |                0 |          2 |                  8 |``  
``| Built-In Windows                           |     15 |                5 |          6 |                 26 |``  
``| NAME - Audit                               |     60 |                5 |         60 |                125 |``  
``| NAME - Debugging                           |     28 |                5 |         34 |                 67 |``  
``| NAME - Protect                             |     28 |                5 |         34 |                 67 |``  
``| NAME - Standard                            |    152 |               28 |         96 |                276 |``  
``| SHWM - Test - May 2020                     |    137 |               28 |         88 |                253 |``  
``+--------------------------------------------+--------+------------------+------------+--------------------+``   
`` ``   
``Process exclusion types by policy``   
``+--------------------------------------------+------+-------+------+--------------------+``   
``| Policy Name                                |   FS |   SPP |   MA |   Total Exclusions |``   
``|--------------------------------------------+------+-------+------+--------------------|``   
``| Built-In Mac                               |    2 |     0 |    0 |                  2 |``   
``| Built-In Windows                           |    3 |     0 |    1 |                  4 |``   
``| NAME - Audit                               |   40 |     3 |    1 |                 44 |``   
``| NAME - Debugging                           |   17 |     2 |    1 |                 20 |``   
``| NAME - Protect                             |   17 |     2 |    1 |                 20 |``   
``| NAME - Standard                            |   84 |    24 |    2 |                110 |``   
``| NAME - Test - May 2020                     |   74 |    24 |    2 |                100 |``   
``+--------------------------------------------+------+-------+------+--------------------+``   
``    FS = File Scan``   
``    SPP = System Process Protection``   
``    MA = Malicious Activity``   
`` ``   
``CAUTION: Policy has close to the maximum of 100 process exceptions.``   
``         "NAME - Test - May 2020" has 100 exceptions``   
`` ``   
``WARNING: Policy exceeds the maximum 100 process exceptions.``   
``         "NAME - Standard" has 110 exceptions``   
