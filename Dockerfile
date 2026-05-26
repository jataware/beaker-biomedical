FROM --platform=linux/amd64 python:3.11.5
RUN useradd -m jupyter && useradd -m user

EXPOSE 8888

RUN apt update && apt install -y lsof rsync curl wget
RUN pip install --upgrade --no-cache-dir hatch pip editables debugpy uv poetry

COPY --chown=1000:1000 . /jupyter
RUN chown -R 1000:1000 /jupyter
WORKDIR /jupyter

RUN rm -f /jupyter/.beaker.conf /jupyter/.env && \
    uv pip install --system -e /jupyter

RUN mkdir -m 777 /var/run/beaker

# Set jupyter user's HOME to point to /jupyter
RUN usermod -d /jupyter jupyter

RUN mkdir -p /jupyter/.local /jupyter/.pqa /jupyter/.config/biopython/Bio/Entrez/DTDs && \
    chown -R 1000:1000 /jupyter/.local /jupyter/.pqa /jupyter/.config

ENV BEAKER_AGENT_USER=jupyter \
    BEAKER_SUBKERNEL_USER=jupyter \
    BEAKER_RUN_PATH=/var/run/beaker \
    BEAKER_DEFAULT_CONTEXT=beaker_biomedical

USER jupyter
RUN mkdir -p /jupyter/.beaker/skills
RUN python /jupyter/fetch-remote-skills.py /jupyter/.beaker/skills

CMD ["python", "-m", "beaker_kernel.app.notebook_app", "--ip", "0.0.0.0", "--allow-root"]
