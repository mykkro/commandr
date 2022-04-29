import os
from commandr import Commandr, load_yaml


if __name__ == "__main__":

    print("Starting Commandr...")

    cmdr = Commandr.from_file("config/demo2.cmdr.yaml")
    args, configs = cmdr.parse()
    print("Args parsed:", args)
    print("Configs loaded:", configs)
