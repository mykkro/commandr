import os, json, itertools, argparse, yaml, sys
import distutils.util
import datetime


def load_yaml(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as infile:
        return yaml.load(infile, Loader=yaml.FullLoader)


def load_json(path):
    with open(path, "r", encoding="utf-8") as infile:
        data = json.load(infile)
    return data


def load_cfg(path):
    if path.endswith(".json"):
        return load_json(path)
    elif path.endswith(".yaml"):
        return load_yaml(path)
    else:
        raise Exception(f"Unsupported config format: {path}")


def environ_or_required(key):
    return (
        {'default': os.environ.get(key)} if os.environ.get(key)
        else {'required': True}
    )


def val_to_bool(val):
    if type(val) == str:
        return bool(distutils.util.strtobool(val))
    else:
        return bool(val)

def val_to_date(val, format):
    return datetime.datetime.strptime(val, format)


def type_by_name(name):
    if name == "str":
        return str
    if name == "int":
        return int
    if name == "float":
        return float

    # other types handle as string ...
    return str


class CommandrArg(object):
    def __init__(self, name, cli, type=None, required=False, default=None, env=None, loadconfig=None, help=help, format=format):
        self.name = name
        self.cli = cli
        self.type = type
        self.default = default
        self.required = required
        self.env = env
        self.loadconfig = loadconfig
        self.help = help
        self.format = format


class Commandr(object):
    def __init__(self):
        self.args = []
        self.parser = None

    @staticmethod
    def from_file(path):
        cfg = load_cfg(path)
        c = Commandr()
        for arg in cfg["args"]:
            c.add_argument(arg["name"], arg["cli"], type=arg.get("type"), required=arg.get("required"), default=arg.get("default"), env=arg.get("env"), loadconfig=arg.get("loadconfig"), help=arg.get("help"), format=arg.get("format"))
        c.build()
        return c

    def add_argument(self, name, cli, type=None, required=False, default=None, env=None, loadconfig=None, help=None, format=None):
        if required and (default is not None):
            raise Exception(f"{name}: Required args cannot have default values!")
        if type == "datetime" and (format is None):
            raise Exception(f"{name}: Datetime fields must have format specified!")
        ca = CommandrArg(name, cli, type=type, required=required, default=default, env=env, loadconfig=loadconfig, help=help, format=format)
        self.args.append(ca)

    def schema_version():
        return "1.0"

    def build(self):
        self.parser, required, optional = Commandr.prepare_cli_args()
        for arg in self.args:
            cli = arg.cli.split("|")
            type = arg.type or'str'
            basictype = type_by_name(type)
            target = required if arg.required else optional
            if type == "switch":
                target.add_argument(*cli, dest=arg.name, help=arg.help, action='store_true')
            else:
                target.add_argument(*cli, dest=arg.name, help=arg.help, type=basictype)
        return self

    def parse(self, args=sys.argv[1:], verbose=False):
        args = self.parser.parse_args()
        args_dict = vars(args)
        out = {}
        configs = {}
        for arg in self.args:
            name = arg.name
            required = arg.required
            cli_val = args_dict.get(name)
            if arg.type == 'bool':
                cli_val = val_to_bool(cli_val)
            default_val = arg.default
            env_val = os.getenv(arg.env) if arg.env else None
            if arg.type in ["switch", "bool"] and arg.env:
                env_val = val_to_bool(env_val)
            if verbose:
                print(f"{name}:")
                print(f"  CLI='{cli_val}' ENV='{env_val}' DEF='{default_val}' REQ={required} LCFG={arg.loadconfig}")

            source = None
            used_value = cli_val
            if (used_value is None) or ((arg.type == "switch") and arg.env and used_value == False):
                used_value = env_val
                if used_value is None:
                    used_value = default_val
                    if used_value is None:
                        if arg.required:
                            raise Exception(f"{name} is required argument, but it is not provided!")
                        source = None
                    else:
                        source = "DEF"
                else:
                    source = "ENV"
            else:
                source = "CLI"

            if arg.type == "datetime" and used_value is not None:
                used_value = val_to_date(used_value, arg.format)

            if arg.loadconfig:
                # the value will be used as path to config file
                configs[name] = load_cfg(used_value)

            if verbose:
                print(f"  source={source} value={used_value}")
            out[name] = dict(source=source, value=used_value)

        self.validate(out)

        return out, configs
        

    def validate(self, out):
        #print("Validating parsed params:", out)
        for arg in self.args:
            name = arg.name
            val = out[name]
            #print("  Validating:", val, arg)

    @staticmethod
    def prepare_cli_args():
        parser = argparse.ArgumentParser()
        optional = parser._action_groups.pop()
        required = parser.add_argument_group('required arguments')
        parser._action_groups.append(optional)
        return parser, required, optional

