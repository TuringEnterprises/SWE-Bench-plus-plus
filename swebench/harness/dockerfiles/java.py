_DOCKERFILE_BASE_JAVA = r"""
FROM eclipse-temurin:{java_version}-jdk-jammy

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y \
wget \
git \
build-essential \
ant \
unzip \
&& rm -rf /var/lib/apt/lists/*

ENV MVND_HOME=/opt/mvnd \
    MAVEN_HOME=/opt/maven \
    PATH=/opt/mvnd/bin:/opt/maven/bin:$PATH

RUN set -eux; \
    ARCH="$(uname -m)"; \
    if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then \
        echo "Installing native mvnd for $ARCH"; \
        curl -fsSL "https://dlcdn.apache.org/maven/mvnd/1.0.2/maven-mvnd-1.0.2-linux-amd64.zip" -o /tmp/mvnd.zip; \
        unzip -q /tmp/mvnd.zip -d /opt; \
        mv /opt/maven-mvnd-1.0.2-linux-amd64 /opt/mvnd; \
        ln -s /opt/mvnd/bin/mvnd /usr/local/bin/mvnd; \
        ln -s /opt/mvnd/bin/mvnd /usr/local/bin/mvn; \
        rm /tmp/mvnd.zip; \
    else \
        echo "No native mvnd for $ARCH, falling back to Maven"; \
        curl -fsSL "https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz" \
          -o /tmp/maven.tgz; \
        mkdir -p "$MAVEN_HOME"; \
        tar -xzf /tmp/maven.tgz -C "$MAVEN_HOME" --strip-components=1; \
        rm /tmp/maven.tgz; \
        # make mvnd an alias so build scripts stay unchanged
        printf '#!/usr/bin/env bash\nexec mvn "$@"\n' > /usr/local/bin/mvnd; \
        chmod +x /usr/local/bin/mvnd; \
    fi

# ENV MVND_HOME=/usr/local/mvnd
# ENV PATH=$MVND_HOME/bin:$PATH

RUN adduser --disabled-password --gecos 'dog' nonroot
"""

_DOCKERFILE_INSTANCE_JAVA = r"""FROM --platform={platform} {env_image_name}

COPY ./setup_repo.sh /root/
RUN /bin/bash /root/setup_repo.sh

WORKDIR /testbed/
"""
