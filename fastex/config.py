"""
FastEx configuration
"""
import os
import logging
import re
from typing import List, Union, TypeVar, Optional, Pattern, Dict, Type, cast, Any

import yamale
import lark
from jinja2 import Template
from lark import Lark

logger = logging.getLogger(__name__)

#: The path to the fastex package directory
_mypath = os.path.dirname(__file__)


# region: schema
class Schema:
    def validate(self, obj: Any) -> bool:
        raise NotImplemented

    @classmethod
    def fromdict(cls: Type['Schema'], obj: dict) -> 'Schema':
        """
        Loads a schema from a dictionary definition.
        Args:
            obj:

        Returns:
        """
        if obj["type"] == "classification":
            return ClassificationSchema.fromdict(obj)
        elif obj["type"] == "text":
            return TextSchema.fromdict(obj)
        else:
            raise ValueError(f"Unsupported schema type: {obj['type']}")


class ClassLabel:
    def __init__(self, name: str, value: str = None):
        self.name = name
        self.value = value or name

    @classmethod
    def fromdict(cls, obj: dict) -> 'ClassLabel':
        return ClassLabel(obj["name"], obj.get("value"))


class ClassificationSchema(Schema):
    def __init__(self, values: List[ClassLabel], allow_multilabel: bool = False):
        self.values = values
        self.allow_multilabel = allow_multilabel

    def validate(self, obj: Union[List[str], str]) -> bool:
        if isinstance(obj, list):
            # Only allow list values if multilabel is true
            if not self.allow_multilabel:
                return False
            return all(any(lbl == value.value for value in self.values) for lbl in obj)
        else:
            return any(obj == value.value for value in self.values)

    @classmethod
    def fromdict(cls: Type['ClassificationSchema'], obj: dict) -> 'ClassificationSchema':
        """
        Loads a schema from a dictionary definition.
        Args:
            obj:

        Returns:
        """
        # We assume that obj has been validated by our schema already, so don't repeat checks here.
        allow_multilabel = obj.get("mode", 'multiclass') == "multilabel"
        values = [ClassLabel.fromdict(value) for value in obj["values"]]
        return cls(values, allow_multilabel)


class TextSchema(Schema):
    def __init__(self, regex_validation: Optional[Pattern] = None,
                 bnf_validation: Optional[Lark] = None):
        self.regex_validation = regex_validation
        self.bnf_validation = bnf_validation

    def validate(self, obj: str) -> bool:
        if self.regex_validation:
            if not self.regex_validation.match(obj):
                return False
        if self.bnf_validation:
            if not self.bnf_validation.parse(obj):
                return False
        return True

    @classmethod
    def fromdict(cls: Type['TextSchema'], obj: dict) -> 'TextSchema':
        # We assume that obj has been validated by our schema already, so don't repeat checks here.
        regex_validation = bnf_validation = None
        if 'regex-validation' in obj:
            regex_validation = re.compile(obj['regex-validation'])
        if 'bnf-validation' in obj:
            bnf_validation = Lark(obj['bnf-validation'])

        return cls(regex_validation, bnf_validation)
# endregion


class Config:
    """
    Stores the configuration of a FastEx server.
    """
    def __init__(self, cfg: dict, path=None):
        self.cfg = cfg
        self._path = path
        #: If we have been provided a path, we track its last modified time so that we can reload
        # when it changes.
        self._last_mtime = self._path and os.stat(self._path).st_mtime
        self._template = Template(self.cfg["template"])
        self._schemas = {name: Schema.fromdict(schema)
                         for name, schema in self.cfg.get("schema", {}).items()}

    @property
    def dirty(self) -> bool:
        """
        Returns:
            If this configuration was created from a file, then we return true iff the timestamp
            of the file has changed since we last loaded it.
        """
        return self._last_mtime is not None and os.stat(self._path).st_mtime != self._last_mtime

    def reload(self):
        """
        Reloads our configuration from file, if one was provided at construction time.
        """
        if self._path:
            logger.info(f"Reloading configuration from {self._path}")
            self.cfg = self._load(self._path)
            self._template = Template(self.cfg["template"])
            self._schemas = {name: Schema.fromdict(schema)
                             for name, schema in self.cfg.get("schema", {}).items()}

    @property
    def template(self):
        return self._template

    @property
    def schemas(self) -> Dict[str, Schema]:
        return self._schemas

    @classmethod
    def _load(cls, path: str) -> dict:
        """
        See `Config.load`
        """
        schema = yamale.make_schema(os.path.join(_mypath, 'templates', 'fex.yamale'))
        logger.info(f"Loading configuration from {path}")
        config = yamale.make_data(path)
        yamale.validate(schema, config)
        logger.info(f"Configuration validated")

        # Yamale's make_data actually loads the data as a tuple of
        # ([objects], filename). We know we have just a single file and object.
        return config[0][0]

    @classmethod
    def load(cls, path: str) -> 'Config':
        """
        Loads and validates a configuration from a YAML file

        Args:
            path: Path to a YAML configuration file

        Returns:
            The contents of the YAML file if it passes schema validation.

        Throws:
            This method throws a `SyntaxError` if the provided YAML file does not parse and a
            `ValueError` if the YAML does not validate against our schema.
        """
        return cls(cls._load(path))


__all__ = ['Config', 'Schema']
