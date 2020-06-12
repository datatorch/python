from typing import get_type_hints
from datatorch.api import ApiClient, Annotation, BoundingBox, Where

client = ApiClient(
    api_key="fa2c325a-fd78-4bc6-827f-90242530bebd", api_url="http://localhost:4000"
)

project = client.project("68ca53cc-5820-4c01-9bf3-abc9e384fff4")
labels = project.labels()

files = project.files(where=Where(path__starts_with="dataset"))
print(len(files))

# f = client.file("7b1e2d05-89ed-40fe-b2aa-9368633b8748")

# anno = Annotation(label=labels[0])
# anno.add(BoundingBox.create(0, 0, 100, 100))

# f.add(anno)
# print(anno.__dict__)
# print(f.__dict__)
