import os
from commandr import Commandr, load_yaml


if __name__ == "__main__":

    print("Starting Commandr...")

    cmdr = Commandr.from_file("config/demo.cmdr.yaml")
    args = cmdr.parse()
    print("Args parsed:", args)
