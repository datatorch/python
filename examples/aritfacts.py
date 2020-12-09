from datatorch import Artifact
import logging


# logging.basicConfig(level=logging.DEBUG)


artifact = Artifact("test/test/test")
artifact.add("./examples/**/*")
# artifact.add("./README.md")
# artifact.add("./pytest.ini")
artifact.commit(message="add readme file")
