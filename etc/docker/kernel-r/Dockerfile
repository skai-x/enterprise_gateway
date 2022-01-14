# Ubuntu 18.04.1 LTS Bionic
ARG BASE_CONTAINER=jupyter/r-notebook:r-4.1.2
FROM $BASE_CONTAINER

ENV PATH=$PATH:$CONDA_DIR/bin

RUN conda install --quiet --yes \
    'r-argparse' && \
    conda clean -tipsy && \
    fix-permissions $CONDA_DIR && \
    fix-permissions /home/jovyan

# Switch back to root to modify ownerships
USER root

RUN apt-get update && apt-get install -y \
    less \
    curl \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*

ADD enterprise_gateway/etc/kernel-launchers/bootstrap/bootstrap-kernel.sh /usr/local/bin/
ADD enterprise_gateway/etc/kernel-launchers/ /usr/local/bin/kernel-launchers

RUN chown jovyan:users /usr/local/bin/bootstrap-kernel.sh && \
	chmod 0755 /usr/local/bin/bootstrap-kernel.sh && \
	chown -R jovyan:users /usr/local/bin/kernel-launchers

USER jovyan
ENV KERNEL_LANGUAGE R
CMD /usr/local/bin/bootstrap-kernel.sh

