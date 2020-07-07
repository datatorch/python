import aiodocker
from .runner import Runner


class DockerRunner(Runner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docker = aiodocker.Docker()

    def execute(self):
        config = {"Image": self.config.get("image")}
        container = self.docker.containers.create(config, name=self.action.identifier)
