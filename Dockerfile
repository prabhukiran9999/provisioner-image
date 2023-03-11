# Start with a base Ubuntu image
FROM ubuntu:latest

# Set environment variables or pass it throgh command line interface
# ENV ANOTHER_VAR=another_value

# Update packages and install Git and GH CLI
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y gnupg && \
    apt-get install -y curl && \
    apt-get install -y apt-utils && \
    curl https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor > /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && \
    apt-get install -y gh

# Install Python and pip
RUN apt-get update && \
    apt-get install -y python3 && \
    apt-get install -y python3-pip

# Set working directory
ENV HOME=/provisioner
COPY . /provisioner
RUN chmod -R g+w ${HOME} && chgrp -R root ${HOME}
WORKDIR /provisioner

# Install any necessary dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Set the command to be run when the container starts
# CMD [ "python3", "script.py" ]
