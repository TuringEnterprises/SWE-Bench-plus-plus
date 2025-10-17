_DOCKERFILE_BASE_JS = r"""
FROM --platform={platform} ubuntu:{ubuntu_version}

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libssl-dev \
    software-properties-common \
    wget \
    gnupg \
    jq \
    ca-certificates \
    dbus \
    ffmpeg \
    imagemagick \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    pkg-config 

# Install node
RUN bash -c "set -eo pipefail && curl -fsSL https://deb.nodesource.com/setup_{node_version}.x | bash -"
RUN apt-get update && apt-get install -y nodejs
RUN node -v && npm -v

# Install pnpm
RUN npm install --global corepack@latest
RUN corepack enable pnpm

# Install Chromium for browser testing
RUN apt-get update && apt-get install -y chromium-browser
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROME_PATH=/usr/bin/chromium-browser

RUN adduser --disabled-password --gecos 'dog' nonroot
"""

_DOCKERFILE_ENV_JS = r"""FROM {base_image_key}

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

COPY ./setup_env.sh /root/
RUN sed -i -e 's/\r$//' /root/setup_env.sh
RUN chmod +x /root/setup_env.sh

ENV NVM_DIR=/usr/local/nvm

# Install Node
ENV NODE_VERSION {node_version}
RUN node -v

# Install Python 3 and Python 2
RUN apt-get update && apt-get install -y python3 python3-pip python2

# Ensure 'python' command points to python3
RUN ln -s /usr/bin/python3 /usr/bin/python

# Test Python installation
RUN python -V && python3 -V && python2 -V

# Set up environment variables for Node
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH
RUN echo "PATH=$PATH:/usr/local/nvm/versions/node/$NODE_VERSION/bin/node" >> /etc/environment

# Install pnpm
RUN npm install -g pnpm@{pnpm_version} --force

# Run the setup script
RUN /bin/bash -c "source ~/.bashrc && /root/setup_env.sh"
RUN node -v
RUN npm -v
RUN pnpm -v
RUN python -V
RUN python2 -V
RUN yarn -v
RUN npx -v

WORKDIR /testbed/
"""

_DOCKERFILE_INSTANCE_JS = r"""FROM {env_image_name}

COPY ./setup_repo.sh /root/
RUN sed -i -e 's/\r$//' /root/setup_repo.sh
RUN node -v
RUN npm -v
RUN /bin/bash /root/setup_repo.sh

WORKDIR /testbed/
"""