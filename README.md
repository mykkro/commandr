# commandr - utility to build command line parsers for Python

Basically, it is a small convenience wrapper around argparse with some useful bits mixed in. 

* uses `argparse` for parsing CLI args
* substitutes values from ENV vars if provided
* can load multiple config files (JSON, YAML) into Python dicts

## Install

This library uses a tiny library [kommons](https://github.com/mykkro/kommons). You can install `kommons` and `commandr` via `python setup.py install`.

## Basic Usage

```python
import os
import sys
from commandr import Commandr, load_yaml

print("Starting Commandr...")

LOADFROMFILE = False
if LOADFROMFILE:
    cmdr = Commandr.load("target/commandr-demo.cmdr.yaml")
else:
    cmdr = Commandr("commandr-demo", title="Commandr Demo")
    cmdr.add_argument("infile", "-i", type="str", required=True)
    cmdr.add_argument("count", "-c|--count", type="int", default=12345, env="COMMANDR_COUNT")
    cmdr.add_argument("config", "--config", default="config/config.yaml", loadconfig="-D")
    cmdr.add_argument("verbose", "-v|--verbose", type="switch", env="COMMANDR_VERBOSE")
    cmdr.add_argument("mybool", "--mybool", type="bool")
    cmdr.add_argument("date", "--date", type="datetime", format="%Y-%m-%d")
    cmdr.add_argument("foo", "--foo", type="int", nargs="+")
    cmdr.add_argument("bar", "--bar", type="str", nargs="*")
    cmdr.add_argument("baz", "--baz", type="float", nargs=3)
        
args, configs = cmdr.parse()

print("Args parsed:")
for argname in args:
    print(f"  ({args[argname]['source']}) {argname}: {args[argname]['value']}") 

print("Configs loaded:", configs)

# cmdr.save("target/commandr-demo.cmdr.yaml")

```

## TODO & Nice2Have

* enhanced args validation
* validate JSON/YAML docs against a schema
