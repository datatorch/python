import sys
import os
from datatorch.core.settings import UserSettings
from datatorch.api.api import ApiClient

def main(folder_path: str, project_id: str):
    if not os.path.exists(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        sys.exit(1)

    # Load user settings
    user_settings = UserSettings()
    api_key = user_settings.api_key
    api_url = user_settings.api_url

    if not api_key or not api_url:
        print("You are not logged in. "
              "Please log in using the `login` command.")
        sys.exit(1)

    # Initialize the API client
    client = ApiClient(api_url=api_url, api_key=api_key)

    # Validate the endpoint
    if not client.validate_endpoint():
        print("Error: Invalid API endpoint.")
        sys.exit(1)
    else:
        print("Valid endpoint")

    # Retrieve the project by ID
    try:
        project = client.project(project_id)
        print(f"\nRetrieved project: {project.name}")
    except Exception as e:
        print(f"Error: Unable to retrieve project with ID '{project_id}'. {e}")
        sys.exit(1)

    # Display available storage links and prompt user selection
    try:
        storage_links = project.storage_links()
        if not storage_links:
            print("No storage available for this project.")
            sys.exit(1)

        print("\nAvailable Storages:")
        for idx, storage_link in enumerate(storage_links):
            print(f"{idx + 1}. {storage_link.name} (ID: {storage_link.id})")

        # Prompt user to select a storage link
        while True:
            try:
                choice = int(input("Enter the number of "
                                   "the storage link to use: "))
                if 1 <= choice <= len(storage_links):
                    selected_storage_link = storage_links[choice - 1]
                    break
                else:
                    print(f"Please enter a number "
                          f"between 1 and {len(storage_links)}.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")

        print(
            f"Selected Storage Link: {selected_storage_link.name} "
            f"(ID: {selected_storage_link.id})\n"
        )

    except Exception as e:
        print(f"Error retrieving storage links: {e}")
        sys.exit(1)

    # Upload files to the selected storage link using its ID
    try:
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                print(f"Uploading file: {file_name}...")
                with open(file_path, "rb") as file:
                    client.upload_to_storage_with_id(
                        storage_id=selected_storage_link.id,
                        file=file,
                        storageFolderName=None,
                        dataset=None,
                    )
        print(f"Upload {file_name} completed successfully!")
    except Exception as e:
        print(f"Error during upload {file_name}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 bulk_upload.py <folder_path> <project_id>")
        sys.exit(1)

    folder_path = sys.argv[1]
    project_id = sys.argv[2]
    main(folder_path, project_id)
