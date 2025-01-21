import os
import click
from datatorch.core.settings import UserSettings
from datatorch.api.api import ApiClient
from spinner import Spinner


@click.command("bulk-upload")
@click.argument("folder_path", type=click.Path(exists=True, file_okay=False))
@click.argument("project_id", type=str)

def bulk_upload(folder_path, project_id):
    """Bulk upload files to a specified project."""

    # Get the list of files to upload
    files = [f for f in os.listdir(folder_path)
             if os.path.isfile(os.path.join(folder_path, f))]
    total_files = len(files)

    if total_files == 0:
        click.echo("No files found in the specified folder.")
        return

    # Load user settings
    user_settings = UserSettings()
    api_key = user_settings.api_key
    api_url = user_settings.api_url

    if not api_key or not api_url:
        click.echo("You are not logged in. "
                   "Please log in using the `login` command.")
        return

    # Initialize the API client
    client = ApiClient(api_url=api_url, api_key=api_key)

    # Validate the endpoint
    if not client.validate_endpoint():
        click.echo("Error: Invalid API endpoint.")
        return
    click.echo("Valid API endpoint verified.")

    # Retrieve the project by ID
    try:
        project = client.project(project_id)
        click.echo(f"Retrieved project: {project.name}")
    except Exception as e:
        click.echo(f"Error: Unable to retrieve "
                   f"project with ID '{project_id}'. {e}")
        return

    # Display available storage links and prompt user selection
    try:
        storage_links = project.storage_links()
        if not storage_links:
            click.echo("No storage available for this project.")
            return

        click.echo("\nAvailable Storages:")
        for idx, storage_link in enumerate(storage_links):
            click.echo(f"{idx + 1}. {storage_link.name} "
                       f"(ID: {storage_link.id})")

        # Prompt user to select a storage link
        while True:
            try:
                choice = int(input("Enter the number of "
                                   "the storage link to use: "))
                if 1 <= choice <= len(storage_links):
                    selected_storage_link = storage_links[choice - 1]
                    break
                else:
                    click.echo(f"Please enter a number "
                               f"between 1 and {len(storage_links)}.")
            except ValueError:
                click.echo("Invalid input. Please enter a valid number.")

        click.echo(f"Selected Storage Link: {selected_storage_link.name} "
                   f"(ID: {selected_storage_link.id})")

    except Exception as e:
        click.echo(f"Error retrieving storage links: {e}")
        return

    # Initialize the spinner
    spinner = Spinner(f"Uploading files (0/{total_files})")

    # Upload files to the selected storage link using its ID
    try:
        for idx, file_name in enumerate(files, start=1):
            file_path = os.path.join(folder_path, file_name)
            spinner.set_text(f"Uploading files ({idx}/{total_files})")
            with open(file_path, "rb") as file:
                client.upload_to_storage_with_id(
                    storage_id=selected_storage_link.id,
                    file=file,
                    storageFolderName=None,
                    dataset=None,
                )
        spinner.done(f"Uploaded all {total_files} files successfully!")
    except Exception as e:
        spinner.done(f"Error during upload: {e}")
        return
