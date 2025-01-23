import os
import datatorch as dt

api = dt.api.ApiClient("your-api-key")
proj = api.project("user-name/project-name")
dset = proj.dataset("data-set-name")

folder_to_upload = "uploadme"
upload_to_storage_id = "your-storage-id"

# Get all the file names in the folder
files = [
    f
    for f in os.listdir(folder_to_upload)
    if os.path.isfile(os.path.join(folder_to_upload, f))
]

# Upload files to the selected storage and dataset using their IDs
try:
    for file_name in files:
        file_path = os.path.join(folder_to_upload, file_name)
        with open(file_path, "rb") as file:
            api.upload_to_filesource(
                project=proj,
                file=file,
                storageId=upload_to_storage_id,
                storageFolderName=None,
                dataset=dset,
            )
except Exception as e:
    print(f"Error Uploading: {e}")
