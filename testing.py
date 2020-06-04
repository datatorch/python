from datatorch.api import ApiClient

client = ApiClient()
project = client.project('5797c4bb-a8f4-405d-b966-558fb6e26b89')
print(project.datasets())
