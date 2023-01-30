import os, argparse, sys
import distutils.util
import datetime
from scalpl import Cut

from kommons import load_cfg, save_cfg, flatten


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


def val_to_type(strvalue, typename):
    if strvalue is None:
        return None
    if typename == 'str':
        return strvalue
    if typename == 'int':
        return int(strvalue)
    if typename == 'float':
        return float(strvalue)
    if typename == 'bool':
        return val_to_bool(strvalue)
    
    raise Exception(f"Cannot convert value: {strvalue}")


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
    def __init__(self, name, cli, type=None, required=False, default=None, metavar=None, env=None, loadconfig=None, help=None, format=None, nargs=None):
        self.name = name
        self.cli = cli
        self.type = type
        self.default = default
        self.required = required
        self.env = env
        self.metavar = metavar
        self.loadconfig = loadconfig
        self.help = help
        self.format = format
        self.nargs = nargs

    def to_dict(self):
        return self.__dict__


class Commandr(object):
    def __init__(self, name, title=None, description=None, epilog=None, usage=None, version=None):
        self.name = name
        self.title = title
        self.description = description
        self.usage = usage
        self.epilog = epilog
        self.version = version
        self.args = []
        self.config_overrides = {}
        self.config_params = {}
        self.parser, self.parser_required, self.parser_optional = self.prepare_cli_args()

        # add parameter: --save-config
        self.add_argument("_saveconfig", "--saveconfig")

    def to_dict(self):
        return dict(name=self.name, title=self.title, description=self.description, usage=self.usage, epilog=self.epilog, version=self.version, schema_version=self.schema_version(), args=[a.to_dict() for a in self.args if a.name != "_saveconfig"])

    def save(self, path):
        save_cfg(path, self.to_dict())

    @staticmethod
    def load(path):
        cfg = load_cfg(path)
        c = Commandr(cfg["name"], title=cfg.get("title"), description=cfg.get("description"), usage=cfg.get("usage"), epilog=cfg.get("epilog"), version=cfg.get("version"))
        for arg in cfg["args"]:
            c.add_argument(arg["name"], arg["cli"], type=arg.get("type"), required=arg.get("required"), default=arg.get("default"), env=arg.get("env"), metavar=arg.get("metavar"), nargs=cfg.get("nargs"), loadconfig=arg.get("loadconfig"), help=arg.get("help"), format=arg.get("format"))
        return c

    def add_argument(self, name, cli, type=None, required=False, default=None, env=None, metavar=None, loadconfig=None, help=None, format=None, nargs=None):
        if required and (default is not None):
            raise Exception(f"{name}: Required args cannot have default values!")
        if type == "datetime" and (format is None):
            raise Exception(f"{name}: Datetime fields must have format specified!")
        if nargs is not None and (loadconfig or type=='switch'):
            raise Exception(f"{name}: Loadconfig or switch args cannot have nargs!")

        arg = CommandrArg(name, cli, type=type, required=required, default=default, metavar=metavar, env=env, loadconfig=loadconfig, help=help, format=format, nargs=nargs)
        self.args.append(arg)

        if loadconfig and isinstance(loadconfig, str):
            self.config_overrides[loadconfig] = name
            self.config_params[name] = {}

        # add to argparse...
        cli = arg.cli.split("|")
        type = arg.type or'str'
        basictype = type_by_name(type)
        target = self.parser_required if arg.required else self.parser_optional
        if type == "switch":
            target.add_argument(*cli, dest=arg.name, help=arg.help, action='store_true')
        else:
            if nargs is not None:
                target.add_argument(*cli, dest=arg.name, help=arg.help, metavar=arg.metavar, type=basictype, nargs=arg.nargs, action='append')
            else:
                target.add_argument(*cli, dest=arg.name, help=arg.help, metavar=arg.metavar, type=basictype)


    def schema_version(self):
        return "1.2"

    def parse(self, args=sys.argv[1:], verbose=False, include_source=False):
        # extract the override params - argparse will not see them
        rest = []
        for arg in args:
            override = False
            for key in self.config_overrides.keys():
                if arg.startswith(key):
                    override = arg
                    break
            if override:
                ovbody = override[len(key):]
                name, value = ovbody.split("=", 1)
                target = self.config_overrides[key]
                self.config_params[target][name] = value
            else:
                rest.append(arg)
            
        args = self.parser.parse_args(rest)
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

                # handle potentioal overrides...
                if arg.name in self.config_params:
                    cp = self.config_params[arg.name]
                    cfg = Cut(configs[name])
                    for key in cp:
                        val = cp[key]
                        if val.startswith("int:"):
                            val = int(val[len("int:"):])
                        elif val.startswith("float:"):
                            val = float(val[len("float:"):])
                        elif val.startswith("bool:"):
                            val = val_to_bool(val[len("bool:"):])

                        cfg[key] = val

            if arg.name == "_saveconfig" and used_value:
                print("Saving config!", used_value)
                self.save(used_value)

            if arg.nargs is not None and used_value:
                used_value = flatten(used_value)

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

    def prepare_cli_args(self):
        parser = argparse.ArgumentParser(usage=self.usage, description=self.description or self.title, epilog=self.epilog)
        optional = parser._action_groups.pop()
        required = parser.add_argument_group('required arguments')
        parser._action_groups.append(optional)
        return parser, required, optional

