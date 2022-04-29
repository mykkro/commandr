# commandr - utility to build command line parsers for Python

Basically, it is a small convenience wrapper around argparse with some useful bits mixed in. 

* uses `argparse` for parsing CLI args
* substitutes values from ENV vars inf provided
* can load multiple config files (JSON, YAML) into Python dicts

## Basic Usage

```
import os
import sys
from commandr import Commandr, load_yaml

cmdr = Commandr()
cmdr.add_argument("infile", "-i", type="str", required=True)
cmdr.add_argument("count", "-c|--count", type="int", default=12345, env="COMMANDR_COUNT")
cmdr.add_argument("config", "--config", default="config/config.yaml", loadconfig=True)
cmdr.add_argument("verbose", "-v|--verbose", type="switch", env="COMMANDR_VERBOSE")
cmdr.build()

args, configs = cmdr.parse(verbose=True)

print("Args parsed:")
for argname in args:
    print(f"  ({args[argname]['source']}) {argname}: {args[argname]['value']}") 

```

## TODO & Nice2Have

* enhanced args validation
* datetime parsing
* validate JSON/YAML docs against a schema