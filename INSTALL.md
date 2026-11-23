# Install aibotlog

Install Python 3.10 or newer. macOS/Linux install with Git (`git+https://...`). Windows uses the GitHub ZIP archive so Git isn't needed there.

## Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install https://github.com/masterxhackerx420-oss/aibotlog/archive/refs/heads/main.zip
.\.venv\Scripts\aibotlog.exe --help
```

No activation or execution-policy change required. aibotlog reads nginx/apache combined log format only. IIS writes W3C format by default, which aibotlog does not parse (those lines are counted as skipped), so point it at nginx/apache logs or switch IIS to a custom NCSA combined format first.

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
