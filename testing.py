from typing import ClassVar, get_type_hints
from datatorch.api import ApiClient, Annotation, BoundingBox

client = ApiClient(api_key='fa2c325a-fd78-4bc6-827f-90242530bebd',
                   api_url='http://localhost:4000')

project = client.project('68ca53cc-5820-4c01-9bf3-abc9e384fff4')
labels = project.labels()

f = client.file('7b1e2d05-89ed-40fe-b2aa-9368633b8748')

anno = Annotation(dict(label_id=labels[0].id))
anno.add(BoundingBox.create(0, 0, 100, 100))

print(anno.to_json())
f.add(anno)
