FROM --platform=linux/amd64 python:3.11.5
RUN useradd -m beaker && useradd -m user

EXPOSE 8888

RUN apt update && apt install -y lsof rsync curl wget
RUN pip install --upgrade --no-cache-dir hatch pip editables debugpy uv poetry

COPY --chown=1000:1000 . /beaker
RUN chown -R 1000:1000 /beaker
WORKDIR /beaker

RUN rm -f /beaker/.beaker.conf /beaker/.env && \
    uv pip install --system --prerelease=allow -e /beaker

RUN mkdir -m 777 /var/run/beaker

# Set beaker user's HOME to point to /beaker
RUN usermod -d /beaker beaker

RUN mkdir -p /beaker/.local /beaker/.config/biopython/Bio/Entrez/DTDs && \
    chown -R 1000:1000 /beaker/.local /beaker/.config

# uncomment: use dev instead of last pypi release

# ADD https://codeload.github.com/jataware/beaker-notebook/tar.gz/dev /tmp/beaker-notebook.tar.gz
# RUN mkdir -p /tmp/beaker-notebook && \
#     tar -xzf /tmp/beaker-notebook.tar.gz -C /tmp/beaker-notebook --strip-components=1
# WORKDIR /tmp/beaker-notebook
# RUN apt install -y npm
# RUN make build && uv pip install --system /tmp/beaker-notebook/dist/*.whl
# WORKDIR /beaker

USER root
ENV BEAKER_AGENT_USER=beaker \
    BEAKER_SUBKERNEL_USER=beaker \
    BEAKER_RUN_PATH=/var/run/beaker \
    BEAKER_DEFAULT_CONTEXT=beaker-biomedical

CMD ["python", "-m", "beaker_notebook.app.server_app", "--ip", "0.0.0.0", "--allow-root"]
