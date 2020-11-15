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
export_path_coco = os.path.join(export_path, "coco.json")
api.download_file(file_id, export_path_coco)

# Load coco json
with open(export_path_coco) as coco_file:
    coco = json.load(coco_file)

# Download the images and write to disk, assumes export format is COCO
for image in coco["images"]:
    # Collect the filename, and the datatorch ID to download via datatorch, and not directly the source Blob, S3 etc.
    file_id = image["datatorch_id"]
    file_name = image["file_name"]
    save_path = os.path.join(export_path, file_name)
    api.download_file(file_id, save_path)
