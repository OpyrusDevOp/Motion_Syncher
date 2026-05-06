# Writing a Custom Function Plugin

Drop a `.py` file anywhere in this `plugins/` directory.  
Motion Syncher scans it at startup and registers every `Function` subclass it finds.

---

## Minimal example

```python
from core.functions.base import Function

class MyFunction(Function):
    TYPE_ID      = "my_function"   # unique ID — used in saved files
    DISPLAY_NAME = "My Function"   # shown in the GUI dropdowns
    DESCRIPTION  = "Does something cool"

    @classmethod
    def config_schema(cls) -> list[dict]:
        return [
            {"key": "message", "label": "Message", "type": "text",
             "placeholder": "Hello!", "default": ""},
        ]

    def __init__(self, message: str = ""):
        self.message = message

    @property
    def name(self) -> str:
        return f"My: {self.message}"

    def execute(self) -> None:
        print(self.message)
```

That's it — no registration call, no import in `__init__.py`.  
Save the file and restart the app.

---

## Class attributes

| Attribute      | Type   | Required | Purpose |
|----------------|--------|----------|---------|
| `TYPE_ID`      | `str`  | yes      | Unique key stored in `.msync.json` save files. Never reuse a TYPE_ID from another plugin or a built-in. |
| `DISPLAY_NAME` | `str`  | no       | Label shown in GUI dropdowns. Falls back to `TYPE_ID`. |
| `DESCRIPTION`  | `str`  | no       | Tooltip / help text (not yet displayed but reserved). |

---

## `config_schema()` field types

Each entry in the list returned by `config_schema()` is a `dict` with these keys:

| Key           | Values / notes |
|---------------|---------------|
| `key`         | Attribute name — must match your `__init__` parameter |
| `label`       | Form label |
| `type`        | `"text"` · `"file"` · `"select"` · `"float"` · `"int"` |
| `placeholder` | Hint text (type `text` / `file`) |
| `filter`      | File-dialog filter (type `file`), e.g. `"Audio (*.mp3 *.wav)"` |
| `options`     | List of strings (type `select`) |
| `min` / `max` | Numeric range (type `float` / `int`) |
| `step`        | Spin-box step (type `float` / `int`) |
| `default`     | Value used when the field is absent from a saved file |

The base class `to_dict()` / `from_dict()` are driven entirely by `config_schema()`,
so **you do not need to override them** as long as your `__init__` parameters match
the `key` names in the schema.

---

## `execute()`

Called from the camera thread — **keep it non-blocking**.  
For anything that might block (network call, heavy disk I/O), spawn a thread or
use `subprocess.Popen` (not `subprocess.run`).

---

## Built-in TYPE_IDs (do not reuse)

| TYPE_ID          | Class                   |
|------------------|-------------------------|
| `audio`          | `AudioFunction`         |
| `shell`          | `ShellFunction`         |
| `keystroke`      | `KeystrokeFunction`     |
| `console`        | `ConsoleWriteFunction`  |

---

## Troubleshooting

- **Plugin not appearing** — Check the terminal for `[PluginLoader]` error lines.  
  Common causes: syntax error in the file, missing `TYPE_ID`, duplicate `TYPE_ID`.
- **Saved project fails to load** — `TYPE_ID` in the `.msync.json` must match exactly.  
  Renaming a `TYPE_ID` breaks old save files.
- **execute() blocks the UI** — Move blocking work to a `threading.Thread` or
  `subprocess.Popen`.
