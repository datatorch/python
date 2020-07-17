from aiodocker import Docker
from aiodocker.containers import DockerContainer

from .runner import Runner


class DockerRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker = Docker()

    async def execute(self):
        container = await self.run_container()
        await container.start()
        async for log in container.log(stdout=True, follow=True):
            print(log)
        await container.stop()
        await self.docker.close()

    async def run_container(self) -> DockerContainer:
        config = {"Image": self.config.get("image")}
        return await self.docker.containers.create(config, name=self.action.identifier)
