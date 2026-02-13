class BaseTool:
    name: str
    description: str
    schema: dict

    async def execute(self, **kwargs) -> dict:
        raise NotImplementedError
