# Install aibotlog

Install Python 3.10 or newer and Git first. Git is needed for the GitHub install URL; alternatively download the repository ZIP, extract it, and run `python -m pip install .` in that folder.

## Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install git+https://github.com/masterxhackerx420-oss/aibotlog
.\.venv\Scripts\aibotlog.exe --help
```

No activation or execution-policy change required. IIS logs are usually under `%SystemDrive%\inetpub\logs\LogFiles` and may need to be in combined format.

## macOS / Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install git+https://github.com/masterxhackerx420-oss/aibotlog
.venv/bin/aibotlog --help
```

If Linux reports venv is unavailable, install your distribution's Python venv package. Do not use sudo pip. Typical nginx or apache logs live under `/var/log/nginx` or `/var/log/apache2` and may require read permission.

## Usage

```sh
aibotlog access.log
aibotlog access.log access.log.1.gz --by path --top 20
aibotlog access.log --json
gzip -dc access.log.gz | aibotlog
aibotlog --help
```

Use the full venv executable path above, or activate your environment to use `aibotlog` directly. Uninstall using your environment's `python -m pip uninstall aibotlog`.
