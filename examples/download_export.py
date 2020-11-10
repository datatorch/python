from datatorch.api import ApiClient
from urllib.parse import urljoin
import requests, json, os

base_url = "https://datatorch.io"

apiUrl = urljoin(base_url, "api/graphql")
exportPath = "./"


# Generate your API key here: datatorch.io/settings/access-tokens
datatorchApiKey = "API Key"  ## replace
api = ApiClient(api_url=apiUrl, api_key=datatorchApiKey)
# Project ID is found in the project Settings of the Datatorch web portal
projectId = "project ID"  ## replace

GetExportQuery = """
  query getProjectExport($id: ID!) {
    projectById(id: $id){
      exportSchemas{ 
        newestExport {
          artifacts {
            id
            name
          }
        }
      }
    }
  }
"""

raw = api.execute(GetExportQuery, params={"id": projectId})

fileDetails = raw["projectById"]["exportSchemas"][0]["newestExport"]["artifacts"][0]
fileId = fileDetails["id"]
fileName = fileDetails["name"]

export_link = urljoin(
    base_url, "/api/file/v1/{0}/{1}?download=true&stream=true".format(fileId, fileName)
)

export_request = requests.get(
    export_link, headers={"datatorch-api-key": datatorchApiKey}
)

if fileName.endswith((".json", ".JSON")):
    export = json.loads(export_request.content)
    # Download the images and write to disk, assumes export format is COCO
    for image in export["images"]:
        # Collect the filename, and the datatorch ID to download via datatorch, and not directly the source Blob, S3 etc.
        fileId = image["datatorch_id"]
        fileName = image["file_name"]

        file_link = urljoin(
            base_url,
            "/api/file/v1/{0}/{1}?download=true&stream=true".format(fileId, fileName),
        )

        file_request = requests.get(
            file_link, headers={"datatorch-api-key": datatorchApiKey}
        )

        save_path = os.path.join(exportPath, fileName)
        export_file = open(save_path, "w+b")
        export_file.write(file_request.content)
        export_file.close()

else:
    # For future export options that may not be JSON based.
    export = export_request.content
