FROM jupyter/scipy-notebook:python-3.9.7

# Fix DL4006
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN if [[ `uname -m` == "aarch64" ]] ; then \
       pip install tensorflow -f https://tf.kmtea.eu/whl/stable.html ; \
    else \
       pip install tensorflow ; \
    fi

ENV KERNEL_LANGUAGE python

ADD jupyter_enterprise_gateway_kernel_image_files*.tar.gz /usr/local/bin/

RUN conda install --quiet --yes \
    pillow \
    future \
    pycryptodomex && \
    fix-permissions $CONDA_DIR

USER root

RUN chown jovyan:users /usr/local/bin/bootstrap-kernel.sh && \
	chmod 0755 /usr/local/bin/bootstrap-kernel.sh && \
	chown -R jovyan:users /usr/local/bin/kernel-launchers

USER jovyan

CMD [ "/usr/local/bin/bootstrap-kernel.sh" ]
