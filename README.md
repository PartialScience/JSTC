# JSTC

## Getting the project running locally

It is recommend that all local development is done in VSCode using the [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Prerequisites

1. Follow the installation docs for the VSCode [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

    This should be a two-step process that first involves installing docker, and then the extension.

### Setting up the dev environment

To set up the dev environment follow these steps:

1. Open the project in VSCode so that the .devcontainer directory is at the root of your open project
2. Withing VSCode hit `Ctrl`+`Shift`+`P` to open the command pallet
3. Enter the following command `Dev Containers: Reopen in Container`

The above steps will build a docker container which is pre-configured to run the project, and then re-open VSCode remotely inside of this container.

Each time you wish to open the project in VSCode you will need to re-run this command to launch in the container, however all subsequent launches will be much faster than the first as the container does not need to be rebuilt each time.
