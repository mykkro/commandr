import os
import sys
import json
from commandr import Commandr


if __name__ == "__main__":

    # Example usage:
    # python main.py -i=foo.bar -c=321 --mybool=1 --date=2022-05-12 -Ddummy-option=int:67890 -v -Dfoo.bar="as df"
    # python main.py -i=foo.bar -c=321 --mybool=1 --date=2022-05-12 -Ddummy-option=int:67890 -v -Dfoo.bar="as df" --foo 123 --foo=456 --foo=890 --bar=hello --bar=fubar --baz 3.14 4.56 1.23

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

 
    args, configs = cmdr.parse(include_source=True)

    if args["verbose"]["value"]:
        print("Args parsed:")
        for argname in args:
            print(f"  ({args[argname]['source']}) {argname}: {args[argname]['value']}") 

        print("Configs loaded:", configs)

    cmdr.save("target/commandr-demo.cmdr.yaml")
