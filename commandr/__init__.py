"""commandr - a small, convenience wrapper around argparse.

Adds environment-variable fallback, JSON/YAML config loading (with CLI
``-D``-style overrides), ``nargs`` support and a save/load-able schema on top
of the standard library's ``argparse``.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Type

from scalpl import Cut

from kommons import environ_or_required, flatten, load_cfg, save_cfg, str_to_bool

__all__ = [
    "Commandr",
    "CommandrArg",
    "environ_or_required",
    "val_to_bool",
    "val_to_date",
    "val_to_type",
    "type_by_name",
]


def val_to_bool(val: Any) -> bool:
    """Convert ``val`` (a string or any other value) into a ``bool``.

    Delegates to :func:`kommons.str_to_bool`, which understands the common
    truthy/falsy spellings (``yes``/``no``, ``true``/``false``, ``1``/``0``, ...).
    """
    return str_to_bool(val)


def val_to_date(val: str, format: str) -> datetime.datetime:
    """Parse ``val`` into a ``datetime`` using the given ``strptime`` ``format``."""
    return datetime.datetime.strptime(val, format)


def val_to_type(strvalue: Optional[str], typename: str) -> Any:
    """Convert a raw string value to the Python type named by ``typename``.

    Supports ``str``/``int``/``float``/``bool``; ``None`` is passed through unchanged.
    """
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

    raise ValueError(f"Cannot convert value: {strvalue}")


def type_by_name(name: str) -> Type:
    """Map a Commandr type name to the built-in Python type used by argparse.

    Only ``str``/``int``/``float`` have a direct argparse type; the other
    Commandr-specific types (``switch``, ``bool``, ``datetime``) are parsed by
    argparse as raw strings and converted afterwards (see ``Commandr.parse``).
    """
    if name == "str":
        return str
    if name == "int":
        return int
    if name == "float":
        return float

    # other types handle as string ...
    return str


class CommandrArg:
    """A single CLI argument definition (name, flags, type, source rules, ...)."""

    def __init__(self, name, cli, type=None, required=False, default=None, metavar=None,
                 env=None, loadconfig=None, help=None, format=None, nargs=None):
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

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


class Commandr:
    """Builds an ``argparse``-based CLI parser with ENV/default fallback and config loading.

    Typical usage::

        cmdr = Commandr("myapp", title="My App")
        cmdr.add_argument("count", "-c|--count", type="int", default=10, env="MYAPP_COUNT")
        args, configs = cmdr.parse()
    """

    def __init__(self, name: str, title: Optional[str] = None, description: Optional[str] = None,
                 epilog: Optional[str] = None, usage: Optional[str] = None,
                 version: Optional[str] = None):
        self.name = name
        self.title = title
        self.description = description
        self.usage = usage
        self.epilog = epilog
        self.version = version
        self.args: List[CommandrArg] = []
        self.config_overrides: Dict[str, str] = {}
        self.config_params: Dict[str, Dict[str, str]] = {}
        self.parser, self.parser_required, self.parser_optional = self.prepare_cli_args()

        # add parameter: --saveconfig
        self.add_argument("_saveconfig", "--saveconfig")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this parser's schema (name/title/description/args/...) to a plain dict."""
        return dict(name=self.name, title=self.title, description=self.description, usage=self.usage,
                    epilog=self.epilog, version=self.version, schema_version=self.schema_version(),
                    args=[a.to_dict() for a in self.args if a.name != "_saveconfig"])

    def save(self, path: str) -> None:
        """Save this parser's schema as a JSON/YAML file at ``path`` (see :func:`kommons.save_cfg`)."""
        save_cfg(path, self.to_dict())

    @staticmethod
    def load(path: str) -> "Commandr":
        """Build a :class:`Commandr` instance from a schema file previously written by :meth:`save`."""
        cfg = load_cfg(path)
        c = Commandr(cfg["name"], title=cfg.get("title"), description=cfg.get("description"),
                     usage=cfg.get("usage"), epilog=cfg.get("epilog"), version=cfg.get("version"))
        for arg in cfg["args"]:
            c.add_argument(arg["name"], arg["cli"], type=arg.get("type"), required=arg.get("required"),
                            default=arg.get("default"), env=arg.get("env"), metavar=arg.get("metavar"),
                            nargs=arg.get("nargs"), loadconfig=arg.get("loadconfig"), help=arg.get("help"),
                            format=arg.get("format"))
        return c

    def add_argument(self, name: str, cli: str, type: Optional[str] = None, required: bool = False,
                      default: Any = None, env: Optional[str] = None, metavar: Optional[str] = None,
                      loadconfig: Optional[Any] = None, help: Optional[str] = None,
                      format: Optional[str] = None, nargs: Optional[Any] = None) -> None:
        """Declare a CLI argument.

        :param name: destination name the parsed value will be stored/returned under.
        :param cli: one or more flags separated by ``|``, e.g. ``"-c|--count"``.
        :param type: one of ``str``/``int``/``float``/``bool``/``switch``/``datetime`` (default ``str``).
        :param required: if ``True`` and no CLI/ENV/default value is found, parsing exits with an error.
        :param default: fallback value used when neither CLI nor ``env`` provide one.
        :param env: name of an environment variable used as a fallback when the flag isn't passed.
        :param metavar: display name for the value in ``--help`` (passed through to argparse).
        :param loadconfig: if truthy, the resolved value is treated as a path to a JSON/YAML config file
            which gets loaded and returned via the ``configs`` dict from :meth:`parse`. If given as a
            string (e.g. ``"-D"``), that prefix also becomes a CLI override syntax, e.g. ``-Dkey=value``
            or ``-Dnested.key=int:5``, applied on top of the loaded config.
        :param help: help text shown in ``--help``.
        :param format: required when ``type="datetime"``; a ``strptime``-compatible format string.
        :param nargs: argparse ``nargs`` value (e.g. ``"+"``, ``"*"``, or an int) for multi-value
            arguments; mutually exclusive with ``loadconfig`` and ``type="switch"``.
        """
        if required and (default is not None):
            raise ValueError(f"{name}: Required args cannot have default values!")
        if type == "datetime" and (format is None):
            raise ValueError(f"{name}: Datetime fields must have format specified!")
        if nargs is not None and (loadconfig or type == 'switch'):
            raise ValueError(f"{name}: Loadconfig or switch args cannot have nargs!")

        arg = CommandrArg(name, cli, type=type, required=required, default=default, metavar=metavar,
                           env=env, loadconfig=loadconfig, help=help, format=format, nargs=nargs)
        self.args.append(arg)

        if loadconfig and isinstance(loadconfig, str):
            self.config_overrides[loadconfig] = name
            self.config_params[name] = {}

        # add to argparse...
        cli_flags = arg.cli.split("|")
        arg_type = arg.type or "str"
        basictype = type_by_name(arg_type)
        target = self.parser_required if arg.required else self.parser_optional
        if arg_type == "switch":
            target.add_argument(*cli_flags, dest=arg.name, help=arg.help, action="store_true")
        elif nargs is not None:
            target.add_argument(*cli_flags, dest=arg.name, help=arg.help, metavar=arg.metavar,
                                 type=basictype, nargs=arg.nargs, action="append")
        else:
            target.add_argument(*cli_flags, dest=arg.name, help=arg.help, metavar=arg.metavar, type=basictype)

    def schema_version(self) -> str:
        return "1.2"

    @staticmethod
    def _coerce(arg: CommandrArg, value: Any) -> Any:
        """Convert a resolved (CLI/ENV/default) value to the type declared for ``arg``.

        ``nargs`` values are left untouched: argparse already applies the basic
        type conversion per occurrence, and the result is flattened separately.
        """
        if value is None or arg.nargs is not None:
            return value
        if arg.type in ("switch", "bool"):
            return val_to_bool(value)
        if arg.type == "datetime":
            return val_to_date(value, arg.format)
        basictype = type_by_name(arg.type or "str")
        return value if isinstance(value, basictype) else basictype(value)

    def _extract_config_overrides(self, args: List[str]) -> List[str]:
        """Pull ``-Dkey=value``-style config overrides out of ``args``; argparse never sees them."""
        rest = []
        for raw_arg in args:
            matched_key = None
            for key in self.config_overrides:
                if raw_arg.startswith(key):
                    matched_key = key
                    break
            if matched_key is not None:
                name, value = raw_arg[len(matched_key):].split("=", 1)
                target = self.config_overrides[matched_key]
                self.config_params[target][name] = value
            else:
                rest.append(raw_arg)
        return rest

    def _load_config_with_overrides(self, arg: CommandrArg, path: str) -> Any:
        """Load the JSON/YAML config file at ``path`` and apply any ``-D``-style overrides onto it."""
        cfg = load_cfg(path)
        overrides = self.config_params.get(arg.name)
        if overrides:
            cut = Cut(cfg)
            for key, raw_val in overrides.items():
                if raw_val.startswith("int:"):
                    val = int(raw_val[len("int:"):])
                elif raw_val.startswith("float:"):
                    val = float(raw_val[len("float:"):])
                elif raw_val.startswith("bool:"):
                    val = val_to_bool(raw_val[len("bool:"):])
                else:
                    val = raw_val
                cut[key] = val
        return cfg

    def parse(self, args: Optional[List[str]] = None, verbose: bool = False,
              include_source: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse CLI arguments, applying the CLI > ENV > default fallback chain.

        :param args: argv list to parse (defaults to ``sys.argv[1:]``); mainly useful for tests.
        :param verbose: if ``True``, prints the resolved value/source of each argument.
        :param include_source: if ``True``, each value in the returned dict is wrapped as
            ``{"source": "CLI"|"ENV"|"DEF"|None, "value": ...}`` instead of being the bare value.
        :returns: a ``(values, configs)`` tuple; ``configs`` holds the loaded data for every
            argument declared with ``loadconfig`` truthy.
        """
        if args is None:
            args = sys.argv[1:]

        rest = self._extract_config_overrides(args)
        namespace = self.parser.parse_args(rest)
        args_dict = vars(namespace)

        values: Dict[str, Any] = {}
        sources: Dict[str, Optional[str]] = {}
        configs: Dict[str, Any] = {}

        for arg in self.args:
            name = arg.name
            cli_val = args_dict.get(name)
            default_val = arg.default
            env_val = os.getenv(arg.env) if arg.env else None

            if verbose:
                print(f"{name}:")
                print(f"  CLI='{cli_val}' ENV='{env_val}' DEF='{default_val}' REQ={arg.required} LCFG={arg.loadconfig}")

            source = None
            used_value = cli_val
            if (used_value is None) or ((arg.type == "switch") and arg.env and used_value is False):
                used_value = env_val
                if used_value is None:
                    used_value = default_val
                    if used_value is None:
                        if arg.required:
                            self.parser.print_help(sys.stderr)
                            sys.exit(1)
                        source = None
                    else:
                        source = "DEF"
                else:
                    source = "ENV"
            else:
                source = "CLI"

            used_value = self._coerce(arg, used_value)

            if arg.loadconfig and used_value is not None:
                # the value is used as a path to a config file
                configs[name] = self._load_config_with_overrides(arg, used_value)

            if arg.name == "_saveconfig" and used_value:
                print("Saving config!", used_value)
                self.save(used_value)

            if arg.nargs is not None and used_value:
                used_value = flatten(used_value)

            if verbose:
                print(f"  source={source} value={used_value}")

            values[name] = used_value
            sources[name] = source

        self.validate(values)

        if include_source:
            out = {name: dict(source=sources[name], value=values[name]) for name in values}
        else:
            out = values

        return out, configs

    def validate(self, values: Dict[str, Any]) -> None:
        """Hook for subclasses/callers to validate parsed values; a no-op by default."""
        for arg in self.args:
            _ = values[arg.name]

    def prepare_cli_args(self) -> Tuple[argparse.ArgumentParser, argparse._ArgumentGroup, argparse._ArgumentGroup]:
        """Create an ``ArgumentParser`` (with this instance's usage/description/epilog) and
        separate 'required'/'optional' argument groups."""
        parser = argparse.ArgumentParser(usage=self.usage, description=self.description or self.title,
                                          epilog=self.epilog)
        optional = parser._action_groups.pop()
        required = parser.add_argument_group('required arguments')
        parser._action_groups.append(optional)
        return parser, required, optional

