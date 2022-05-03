import os, argparse, sys
import distutils.util
import datetime

from kommons import load_cfg, save_cfg


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

    def to_dict(self):
        return self.__dict__


class Commandr(object):
    def __init__(self, name, title=None, description=None, version=None):
        self.name = name
        self.title = title
        self.description = description
        self.version = version
        self.args = []
        self.parser, self.parser_required, self.parser_optional = Commandr.prepare_cli_args()

    def to_dict(self):
        return dict(name=self.name, title=self.title, description=self.description, version=self.version, schema_version=self.schema_version(), args=[a.to_dict() for a in self.args])

    def save(self, path):
        save_cfg(path, self.to_dict())

    @staticmethod
    def load(path):
        cfg = load_cfg(path)
        c = Commandr(cfg["name"], title=cfg.get("title"), description=cfg.get("description"), version=cfg.get("version"))
        for arg in cfg["args"]:
            c.add_argument(arg["name"], arg["cli"], type=arg.get("type"), required=arg.get("required"), default=arg.get("default"), env=arg.get("env"), loadconfig=arg.get("loadconfig"), help=arg.get("help"), format=arg.get("format"))
        return c

    def add_argument(self, name, cli, type=None, required=False, default=None, env=None, loadconfig=None, help=None, format=None):
        if required and (default is not None):
            raise Exception(f"{name}: Required args cannot have default values!")
        if type == "datetime" and (format is None):
            raise Exception(f"{name}: Datetime fields must have format specified!")
        arg = CommandrArg(name, cli, type=type, required=required, default=default, env=env, loadconfig=loadconfig, help=help, format=format)
        self.args.append(arg)

        # add to argparse...
        cli = arg.cli.split("|")
        type = arg.type or'str'
        basictype = type_by_name(type)
        target = self.parser_required if arg.required else self.parser_optional
        if type == "switch":
            target.add_argument(*cli, dest=arg.name, help=arg.help, action='store_true')
        else:
            target.add_argument(*cli, dest=arg.name, help=arg.help, type=basictype)


    def schema_version(self):
        return "1.0"

    def parse(self, args=sys.argv[1:], verbose=False, include_source=False):
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
                            # raise Exception(f"{name} is required argument, but it is not provided!")
                            self.parser.print_help(sys.stderr)
                            sys.exit(1)

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

            if include_source:
                out[name] = dict(source=source, value=used_value)
            else:
                out[name] = used_value

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

