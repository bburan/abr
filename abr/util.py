import json
from pathlib import Path
from enaml.qt.QtCore import QStandardPaths


def config_path():
    config_path = Path(QStandardPaths.standardLocations(QStandardPaths.GenericConfigLocation)[0])
    return config_path / 'OHSU' / 'abr'


def config_file():
    config_file =  config_path() / 'config.json'
    config_file.parent.mkdir(exist_ok=True, parents=True)
    return config_file


def read_config():
    filename = config_file()
    if not filename.exists():
        return {}
    return json.loads(filename.read_text())


def write_config(config):
    filename = config_file()
    filename.write_text(json.dumps(config, indent=2))
