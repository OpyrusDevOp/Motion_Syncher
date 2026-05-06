from abc import ABC, abstractmethod


class Function(ABC):
    """
    Base class for all triggerable actions.

    Subclasses MUST set TYPE_ID (unique string used for serialization).
    DISPLAY_NAME and DESCRIPTION are shown in the GUI.

    If config_schema() is implemented, the default to_dict() and from_dict()
    work automatically — no need to override them for simple functions.
    """

    TYPE_ID: str = ""         # e.g. "shell", "audio"  — must be unique
    DISPLAY_NAME: str = ""    # shown in function-type dropdowns
    DESCRIPTION: str = ""     # tooltip / help text

    @classmethod
    def config_schema(cls) -> list[dict]:
        """
        Describes configuration fields for the GUI form builder.

        Each entry is a dict with:
          key:         str   — attribute name (must match __init__ parameter)
          label:       str   — form label
          type:        str   — "text" | "file" | "select" | "float" | "int"
          placeholder: str   — hint text  (type "text")
          filter:      str   — file dialog filter  (type "file")
          options:     list  — choices  (type "select")
          min/max:     num   — range  (type "float" | "int")
          step:        num   — spin step  (type "float" | "int")
          default:     any   — value used when field is absent
        """
        return []

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Short human-readable label shown in the choreography list."""
        ...

    @abstractmethod
    def execute(self) -> None:
        """Fire the action. Called from the camera thread — keep it non-blocking."""
        ...

    # ------------------------------------------------------------------
    # Serialization — default implementations driven by config_schema()
    # Override only if your function needs custom serialization.
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        d: dict = {"type": self.TYPE_ID}
        for field in self.config_schema():
            d[field["key"]] = getattr(self, field["key"], field.get("default", ""))
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Function":
        kwargs: dict = {}
        for field in cls.config_schema():
            key = field["key"]
            val = data.get(key, field.get("default", ""))
            ftype = field.get("type", "text")
            if ftype == "float":
                val = float(val)
            elif ftype == "int":
                val = int(val)
            kwargs[key] = val
        return cls(**kwargs)
