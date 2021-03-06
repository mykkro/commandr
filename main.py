import os
import sys
import json
from commandr import Commandr


if __name__ == "__main__":

    # Example usage:
    # python main.py -i=foo.bar -c=321 --mybool=1 --date=2022-05-12

    print("Starting Commandr...")

    LOADFROMFILE = True
    if LOADFROMFILE:
        cmdr = Commandr.load("target/commandr-demo.cmdr.yaml")
    else:
        cmdr = Commandr("commandr-demo", title="Commandr Demo")
        cmdr.add_argument("infile", "-i", type="str", required=True)
        cmdr.add_argument("count", "-c|--count", type="int", default=12345, env="COMMANDR_COUNT")
        cmdr.add_argument("config", "--config", default="config/config.yaml", loadconfig=True)
        cmdr.add_argument("verbose", "-v|--verbose", type="switch", env="COMMANDR_VERBOSE")
        cmdr.add_argument("mybool", "--mybool", type="bool")
        cmdr.add_argument("date", "--date", type="datetime", format="%Y-%m-%d")
 
    args, configs = cmdr.parse()
    print("Args parsed:")
    for argname in args:
        print(f"  {argname}: {args[argname]}") 
    print()

    args, configs = cmdr.parse(include_source=True)
    print("Args parsed (incl sources):")
    for argname in args:
        print(f"  ({args[argname]['source']}) {argname}: {args[argname]['value']}") 
    print()

    print("Configs loaded:", configs)

    cmdr.save("target/commandr-demo.cmdr.yaml")
