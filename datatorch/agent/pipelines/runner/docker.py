import asyncio

from aiodocker import Docker
from aiodocker.containers import DockerContainer

from .runner import Runner


class DockerRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker = Docker()

    async def execute(self):
        container = await self.run_container()
        try:
            await container.start()
            async for log in container.log(stdout=True, follow=True):
                print(log)
            await container.stop()
        except asyncio.CancelledError:
            # Step canceled/timed out server-side — stop the container so it
            # doesn't outlive the step.
            try:
                await container.stop()
            except Exception:
                pass
            raise
        finally:
            await self.docker.close()

    async def run_container(self) -> DockerContainer:
        config = {"Image": self.config.get("image")}
        return await self.docker.containers.create(config, name=self.action.identifier)
