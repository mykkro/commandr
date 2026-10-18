"""Unit tests for the commandr package."""
import datetime

import pytest

from commandr import Commandr, CommandrArg, type_by_name, val_to_bool, val_to_date, val_to_type


class TestValToBool:
    def test_truthy_string(self):
        assert val_to_bool("true") is True

    def test_falsy_string(self):
        assert val_to_bool("false") is False

    def test_non_string_value(self):
        assert val_to_bool(1) is True
        assert val_to_bool(0) is False


class TestValToDate:
    def test_parses_with_format(self):
        assert val_to_date("2022-05-12", "%Y-%m-%d") == datetime.datetime(2022, 5, 12)


class TestValToType:
    def test_none_passes_through(self):
        assert val_to_type(None, "int") is None

    def test_str(self):
        assert val_to_type("hello", "str") == "hello"

    def test_int(self):
        assert val_to_type("42", "int") == 42

    def test_float(self):
        assert val_to_type("3.14", "float") == 3.14

    def test_bool(self):
        assert val_to_type("true", "bool") is True

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            val_to_type("x", "unknown")


class TestTypeByName:
    @pytest.mark.parametrize("name,expected", [("str", str), ("int", int), ("float", float)])
    def test_known_types(self, name, expected):
        assert type_by_name(name) is expected

    @pytest.mark.parametrize("name", ["bool", "switch", "datetime", "unknown"])
    def test_unknown_types_fall_back_to_str(self, name):
        assert type_by_name(name) is str


class TestCommandrArg:
    def test_defaults_are_none(self):
        arg = CommandrArg("name", "-n")
        assert arg.help is None
        assert arg.format is None
        assert arg.nargs is None
        assert arg.metavar is None

    def test_to_dict_round_trips(self):
        arg = CommandrArg("count", "-c|--count", type="int", default=5)
        d = arg.to_dict()
        assert d["name"] == "count"
        assert d["cli"] == "-c|--count"
        assert d["type"] == "int"
        assert d["default"] == 5

    def test_to_dict_returns_a_copy(self):
        arg = CommandrArg("count", "-c|--count", type="int")
        d = arg.to_dict()
        d["type"] = "mutated"
        assert arg.type == "int"


def new_commandr(**kwargs):
    """Build a bare Commandr and strip the auto-added `--saveconfig` from the args list length checks."""
    return Commandr("app", **kwargs)


class TestAddArgument:
    def test_required_with_default_raises(self):
        cmdr = new_commandr()
        with pytest.raises(ValueError):
            cmdr.add_argument("foo", "--foo", required=True, default="x")

    def test_datetime_without_format_raises(self):
        cmdr = new_commandr()
        with pytest.raises(ValueError):
            cmdr.add_argument("date", "--date", type="datetime")

    def test_nargs_with_loadconfig_raises(self):
        cmdr = new_commandr()
        with pytest.raises(ValueError):
            cmdr.add_argument("foo", "--foo", loadconfig=True, nargs="+")

    def test_nargs_with_switch_raises(self):
        cmdr = new_commandr()
        with pytest.raises(ValueError):
            cmdr.add_argument("foo", "--foo", type="switch", nargs="+")

    def test_saveconfig_is_auto_added(self):
        cmdr = new_commandr()
        assert any(a.name == "_saveconfig" for a in cmdr.args)

    def test_saveconfig_excluded_from_schema(self):
        cmdr = new_commandr()
        assert all(a["name"] != "_saveconfig" for a in cmdr.to_dict()["args"])


class TestParseBasicTypes:
    def test_cli_string_value(self):
        cmdr = new_commandr()
        cmdr.add_argument("infile", "-i", type="str", required=True)
        out, _ = cmdr.parse(["-i", "foo.txt"])
        assert out["infile"] == "foo.txt"

    def test_cli_int_value_is_cast(self):
        cmdr = new_commandr()
        cmdr.add_argument("count", "-c|--count", type="int", default=1)
        out, _ = cmdr.parse(["-c", "42"])
        assert out["count"] == 42
        assert isinstance(out["count"], int)

    def test_default_value_used_when_absent(self):
        cmdr = new_commandr()
        cmdr.add_argument("count", "-c|--count", type="int", default=12345)
        out, _ = cmdr.parse([])
        assert out["count"] == 12345

    def test_missing_required_arg_exits(self):
        cmdr = new_commandr()
        cmdr.add_argument("infile", "-i", type="str", required=True)
        with pytest.raises(SystemExit):
            cmdr.parse([])


class TestParseEnvFallback:
    def test_env_fallback_used_when_cli_absent(self, monkeypatch):
        monkeypatch.setenv("APP_COUNT", "99")
        cmdr = new_commandr()
        cmdr.add_argument("count", "-c|--count", type="int", default=1, env="APP_COUNT")
        out, _ = cmdr.parse([])
        assert out["count"] == 99
        # regression test: env values must be cast to the declared type, just
        # like CLI values are cast by argparse.
        assert isinstance(out["count"], int)

    def test_cli_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("APP_COUNT", "99")
        cmdr = new_commandr()
        cmdr.add_argument("count", "-c|--count", type="int", default=1, env="APP_COUNT")
        out, _ = cmdr.parse(["-c", "7"])
        assert out["count"] == 7

    def test_env_fallback_for_bool_type(self, monkeypatch):
        # regression test: a "bool" (non-switch) argument used to always
        # resolve to False when not passed on the CLI, ignoring ENV/default.
        monkeypatch.setenv("APP_FLAG", "true")
        cmdr = new_commandr()
        cmdr.add_argument("flag", "--flag", type="bool", env="APP_FLAG")
        out, _ = cmdr.parse([])
        assert out["flag"] is True

    def test_default_used_for_bool_type_when_no_cli_or_env(self, monkeypatch):
        monkeypatch.delenv("APP_FLAG_MISSING", raising=False)
        cmdr = new_commandr()
        cmdr.add_argument("flag", "--flag", type="bool", default=True, env="APP_FLAG_MISSING")
        out, _ = cmdr.parse([])
        assert out["flag"] is True


class TestParseSwitch:
    def test_switch_true_when_passed(self):
        cmdr = new_commandr()
        cmdr.add_argument("verbose", "-v|--verbose", type="switch")
        out, _ = cmdr.parse(["-v"])
        assert out["verbose"] is True

    def test_switch_false_by_default(self):
        cmdr = new_commandr()
        cmdr.add_argument("verbose", "-v|--verbose", type="switch")
        out, _ = cmdr.parse([])
        assert out["verbose"] is False

    def test_switch_env_fallback_when_not_passed(self, monkeypatch):
        monkeypatch.setenv("APP_VERBOSE", "true")
        cmdr = new_commandr()
        cmdr.add_argument("verbose", "-v|--verbose", type="switch", env="APP_VERBOSE")
        out, _ = cmdr.parse([])
        assert out["verbose"] is True


class TestParseDatetime:
    def test_datetime_parsed_with_format(self):
        cmdr = new_commandr()
        cmdr.add_argument("date", "--date", type="datetime", format="%Y-%m-%d")
        out, _ = cmdr.parse(["--date", "2022-05-12"])
        assert out["date"] == datetime.datetime(2022, 5, 12)


class TestParseNargs:
    def test_nargs_plus_collects_repeated_flags(self):
        cmdr = new_commandr()
        cmdr.add_argument("foo", "--foo", type="int", nargs="+")
        out, _ = cmdr.parse(["--foo", "1", "2", "--foo", "3"])
        assert out["foo"] == [1, 2, 3]

    def test_nargs_fixed_count(self):
        cmdr = new_commandr()
        cmdr.add_argument("baz", "--baz", type="float", nargs=3)
        out, _ = cmdr.parse(["--baz", "1.1", "2.2", "3.3"])
        assert out["baz"] == [1.1, 2.2, 3.3]

    def test_nargs_absent_defaults_to_none(self):
        cmdr = new_commandr()
        cmdr.add_argument("foo", "--foo", type="int", nargs="+")
        out, _ = cmdr.parse([])
        assert out["foo"] is None


class TestParseIncludeSource:
    def test_marks_source_of_each_value(self, monkeypatch):
        monkeypatch.setenv("APP_COUNT", "99")
        cmdr = new_commandr()
        cmdr.add_argument("infile", "-i", type="str", required=True)
        cmdr.add_argument("count", "-c|--count", type="int", default=1, env="APP_COUNT")
        out, _ = cmdr.parse(["-i", "foo.txt"], include_source=True)
        assert out["infile"] == {"source": "CLI", "value": "foo.txt"}
        assert out["count"] == {"source": "ENV", "value": 99}


class TestParseLoadConfig:
    def test_loads_config_file_referenced_by_argument(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"key": "value"}')
        cmdr = new_commandr()
        cmdr.add_argument("config", "--config", default=str(cfg_file), loadconfig=True)
        out, configs = cmdr.parse([])
        assert out["config"] == str(cfg_file)
        assert configs["config"] == {"key": "value"}

    def test_loadconfig_without_value_does_not_crash(self):
        # regression test: an optional loadconfig argument with no default/env
        # and not provided on the CLI used to crash trying to load path=None.
        cmdr = new_commandr()
        cmdr.add_argument("config", "--config", loadconfig=True)
        out, configs = cmdr.parse([])
        assert out["config"] is None
        assert "config" not in configs

    def test_dash_d_override_applies_on_top_of_config(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"dummy-option": 12345, "foo": {"bar": "hello"}}')
        cmdr = new_commandr()
        cmdr.add_argument("config", "--config", default=str(cfg_file), loadconfig="-D")
        out, configs = cmdr.parse(["-Ddummy-option=int:67890", "-Dfoo.bar=world"])
        assert configs["config"]["dummy-option"] == 67890
        assert configs["config"]["foo"]["bar"] == "world"


class TestSaveConfig:
    def test_saveconfig_writes_schema_file(self, tmp_path):
        out_file = tmp_path / "saved.json"
        cmdr = new_commandr()
        cmdr.add_argument("infile", "-i", type="str", required=True)
        cmdr.parse(["-i", "foo.txt", "--saveconfig", str(out_file)])
        assert out_file.exists()


class TestSaveLoadSchema:
    def test_save_and_load_round_trip(self, tmp_path):
        path = tmp_path / "schema.yaml"
        cmdr = Commandr("app", title="App", description="desc")
        cmdr.add_argument("infile", "-i", type="str", required=True)
        cmdr.add_argument("count", "-c|--count", type="int", default=5, env="APP_COUNT")
        cmdr.save(str(path))

        loaded = Commandr.load(str(path))
        assert loaded.name == "app"
        assert loaded.title == "App"
        assert [a.name for a in loaded.args if a.name != "_saveconfig"] == ["infile", "count"]

        out, _ = loaded.parse(["-i", "foo.txt"])
        assert out["infile"] == "foo.txt"
        assert out["count"] == 5
