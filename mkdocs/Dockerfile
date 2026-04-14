FROM python:3.12-slim

RUN pip config set global.index-url https://pypi.mirrors.ustc.edu.cn/simple/

RUN pip install --no-cache-dir mkdocs==1.5.3 mkdocs-material==9.5.3

WORKDIR /docs

EXPOSE 8000

CMD ["mkdocs", "serve", "-f", "mkdocs/mkdocs.yml", "--dev-addr=0.0.0.0:8000"]
