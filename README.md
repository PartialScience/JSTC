# JSTC

## Getting the project running locally

It is recommend that all local development is done in VSCode using the [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Prerequisites

1. Follow the installation docs for the VSCode [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

    This should be a two-step process that first involves installing docker, and then the extension.

### Setting up the dev environment

To set up the dev environment follow these steps:

1. Open the project in VSCode so that the .devcontainer directory is at the root of your open project
2. Within VSCode hit `Ctrl`+`Shift`+`P` to open the command pallet
3. Enter the following command `Dev Containers: Reopen in Container`
4. VSCode will reopen and build the dev enviornment. Wait until the dev container is done setting up before you attempt to run any code. Note that even after the files show up in VSCode the configuration will continue for several more minutes. You can watch the progress by pressing `ctrl`+`j` and navigating to the terminals tab. Or by clicking on the info button when the dev container popup shows up in the bottom right of the screen

The above steps will build a docker container which is pre-configured to run the project, and then re-open VSCode remotely inside of this container.

Each time you wish to open the project in VSCode you will need to re-run this command to launch in the container, however all subsequent launches will be much faster than the first as the container does not need to be rebuilt each time.

