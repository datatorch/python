from datatorch.api import ApiClient

client = ApiClient(api_key='fa2c325a-fd78-4bc6-827f-90242530bebd',
                   api_url='http://localhost:4000')

viewer = client.viewer()
print(viewer.to_json())
