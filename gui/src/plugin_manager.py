import json
import os


class Parameter():
    def __init__(self, type: str, name: str, symbol: str, mode: str,
                 value: float, min: float, max: float):
        self.type = type
        self.name = name
        self.symbol = symbol
        self.mode = mode
        self.value = value
        self.minimum = min
        self.max = max
        match self.mode:
            case "dial":
                self.increment = (max - min)/100
            case "button" | "selector":
                self.increment = 1

    def setValue(self, value: float):
        self.value = value


class Plugin():
    def __init__(
        self,
        name: str,
        uri: str,
        channels: str,
        inputs: list,
        outputs: list,
        bypass: float = 0,
        paramters: list = None,
        category: str | None = None,
        description: str | None = None,
    ):
        self.name = name
        self.uri = uri
        self.bypass = bypass
        self.channels = channels
        self.inputs = inputs
        self.outputs = outputs
        # initalize parameters if there are any otherwise initalize an empty list
        self.parameters = paramters if paramters else []
        self.category = category
        self.description = description

    def add_parameter(self, parameter: Parameter):
        self.parameters.append(parameter)

    def clone(self):
        return Plugin(
            name=self.name,
            uri=self.uri,
            channels=self.channels,
            inputs=list(self.inputs),
            outputs=list(self.outputs),
            bypass=self.bypass,
            category=self.category,
            description=self.description,
            paramters=[
                Parameter(
                    type=param.type,
                    name=param.name,
                    symbol=param.symbol,
                    mode=param.mode,
                    value=param.value,
                    min=param.minimum,
                    max=param.max,
                ) for param in self.parameters
            ]
        )


class PluginManager:
    def __init__(self, plugins: list = None):
        self.plugins = plugins if plugins else []

    def getPluginNames(self):
        names = []
        for plugin in self.plugins:
            names.append(plugin.name)
        return names

    def getParameterNames(self, x: int):
        try:
            names = []
            for parameter in self.plugins[x].parameters:
                names.append(parameter.name)

            return names
        except Exception as e:
            print(e)
            return []

    def size(self):
        return len(self.plugins)

    def paramSize(self, x: int):
        return len(self.plugins[x].parameters)

    def getPlugin(self, x: int):
        try:
            return self.plugins[x]
        except IndexError:
            print("Index does not exist")
            return []

    def addPlugin(self, plugin: Plugin):
        self.plugins.append(plugin)

    def changeParameter(self, pluginIndex: int, parameterIndex: int,
                        value: float):
        try:
            plugin = self.plugins[pluginIndex]
            try:
                parameter = plugin.parameters[parameterIndex]
                parameter.setValue(value)

            except IndexError:
                print("Parameter index does not exist")
                return None

        except IndexError:
            print("Plugin index does not exist")
            return None

    def initFromJSON(self, jsonFile: str):
        try:
            with open(jsonFile, "r") as file:
                data = json.load(file)
                if "plugins" not in data:
                    raise ValueError("Missing 'plugins' field")

                for plugin_data in data["plugins"]:
                    try:
                        self.addPlugin(self.parse_plugin_data(plugin_data))
                    except ValueError as e:
                        print(f"Skipping plugin in {jsonFile}: {e}")

        except json.JSONDecodeError:
            print("Invalid JSON format!")
            return -1
        except FileNotFoundError:
            print("Invalid path to JSON")
            return -1
        except ValueError as e:
            print(f"JSON Error: {e}")

    @staticmethod
    def parse_plugin_data(plugin_data: dict):
        name = plugin_data.get("name", "plugin")
        if "uri" not in plugin_data:
            raise ValueError("No uri included")
        uri = plugin_data.get("uri")
        bypass = plugin_data.get("bypass", 0)
        channels = plugin_data.get("channels", "mono")
        inputs = plugin_data.get("inputs", ["in"])
        outputs = plugin_data.get("outputs", ["out"])
        category = plugin_data.get("category")
        description = plugin_data.get("description")

        parameters = []

        for param_data in plugin_data.get("parameters", []):
            try:
                parameter = Parameter(
                    type=param_data.get("type", "lv2"),
                    name=param_data.get("name", "parameter"),
                    symbol=param_data["symbol"],
                    mode=param_data.get("mode", "dial"),
                    min=param_data["min"],
                    max=param_data["max"],
                    value=param_data.get("default", 1.0)
                )
                parameters.append(parameter)
            except KeyError as e:
                print(f"Skipping parameter {name} due to missing key: {e}")
        return Plugin(
            name=name,
            uri=uri,
            bypass=bypass,
            channels=channels,
            inputs=inputs,
            outputs=outputs,
            category=category,
            description=description,
            paramters=parameters
        )


def load_plugin_manifests(manifest_dir: str):
    plugins = []
    if not os.path.isdir(manifest_dir):
        return plugins

    for filename in sorted(os.listdir(manifest_dir)):
        if not filename.endswith(".json"):
            continue
        file_path = os.path.join(manifest_dir, filename)
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            print(f"Invalid plugin manifest JSON format: {file_path}")
            continue
        except FileNotFoundError:
            print(f"Manifest not found: {file_path}")
            continue

        plugin_entries = []
        if isinstance(data, dict) and "plugins" in data:
            plugin_entries = data["plugins"]
        elif isinstance(data, dict):
            plugin_entries = [data]

        for plugin_data in plugin_entries:
            try:
                plugins.append(PluginManager.parse_plugin_data(plugin_data))
            except ValueError as e:
                print(f"Skipping plugin in {file_path}: {e}")

    return plugins
