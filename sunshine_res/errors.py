class OutputNotFound(ValueError):
    def __init__(self, cmd: str, output_name: str | None):
        self.cmd: str = cmd
        self.output_name: str | None = output_name

        msg: str
        if not self.output_name:
            msg = f"Could not find default output. Check {self.cmd}."
        else:
            msg = f"Could not find output named {self.output_name}. Check {self.cmd}"

        super().__init__(msg)


class CurrentModeNotFound(ValueError):
    def __init__(self, cmd: str, output_name: str):
        self.cmd: str = cmd
        self.output_name: str = output_name

        super().__init__(
            f"Could not identify current mode for output named {self.output_name}. Check {self.cmd}"
        )
