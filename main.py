import os
import sys
from commandr import Commandr, load_yaml


if __name__ == "__main__":

    # Example usage:
    # python main.py -i=foo.bar -c=321 --mybool=1 --date=2022-05-12

    print("Starting Commandr...")

    cmdr = Commandr()
    cmdr.add_argument("infile", "-i", type="str", required=True)
    cmdr.add_argument("count", "-c|--count", type="int", default=12345, env="COMMANDR_COUNT")
    cmdr.add_argument("config", "--config", default="config/config.yaml", loadconfig=True)
    cmdr.add_argument("verbose", "-v|--verbose", type="switch", env="COMMANDR_VERBOSE")
    cmdr.add_argument("mybool", "--mybool", type="bool")
    cmdr.add_argument("date", "--date", type="datetime", format="%Y-%m-%d")
    cmdr.build()

    args, configs = cmdr.parse()

    print("Args parsed:")
    for argname in args:
        print(f"  ({args[argname]['source']}) {argname}: {args[argname]['value']}") 

    print("Configs loaded:", configs)
