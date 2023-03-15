from datatorch import ApiClient

import json, os


export_path = "./"
# Project ID is found in the project Settings of the Datatorch web portal
project_id = "project ID"  ## replace

api = ApiClient()


# GraphQL to get export info.
GetNewestExport = """
  query GetNewestExport($id: ID!) {
    project: projectById(id: $id){
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

raw = api.execute(GetNewestExport, params={"id": project_id})

file_info = raw["project"]["exportSchemas"][0]["newestExport"]["artifacts"][0]
file_id = file_info["id"]
file_name = file_info["name"]

# Download coco json
exportPath, result = api.download_file(file_id, "coco.json", export_path)

# Load coco json
with open(exportPath) as coco_file:
    coco = json.load(coco_file)

# Download the images and write to disk, assumes export format is COCO
for image in coco["images"]:
    # Collect the filename, and the datatorch ID to download via datatorch, and not directly the source Blob, S3 etc.
    file_id = image["datatorch_id"]
    file_name = image["file_name"]
    api.download_file(file_id, file_name, export_path)
