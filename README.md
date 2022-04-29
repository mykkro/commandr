# commandr - utility to build command line poarsers for Python

* uses `argparse` for parsing CLI args
* substitutes values from ENV vars inf provided
* can load multuiple config files into Python dicts

## Basic Usage

```
    cmdr = Commandr.from_file("config/demo2.cmdr.yaml")
    args, configs = cmdr.parse()
    print("Args parsed:", args)
    print("Configs loaded:", configs)
```