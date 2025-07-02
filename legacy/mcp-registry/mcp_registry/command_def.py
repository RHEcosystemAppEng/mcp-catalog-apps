from mcp_registry.utils import logger


class CommandDef:
    def __init__(self, command: str, version: str = "latest"):
        self.command = command
        self.version = version
        self.args = []
        self.env_vars = {}

    def add_arg(self, arg: str):
        self.args.append(arg)

    def add_args(self, args: list[str]):
        self.args.extend(args)

    def add_env_var(self, name: str, value: str):
        logger.info(f"Adding environment variable: {name}={value}")
        self.env_vars[name] = value

    def to_manifest_args(self):
        return " ".join(self.args)

    def to_manifest_env_vars(self):
        return " ".join([f"{k}={v}" for k, v in self.env_vars.items()])

    def __str__(self):
        return f"{self.command} {self.to_manifest_args()} {self.to_manifest_env_vars()}"
