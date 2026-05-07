# CeRAI AIEvaluationTool - Audit Log

## 1. Installation Attempt
**Command:** `pip install -r requirements.txt`

**Output / Errors:**
```text
Collecting selenium (from -r requirements.txt (line 1))
  Downloading selenium-4.43.0-py3-none-any.whl.metadata (7.5 kB)
...
Collecting sarvamai (from -r requirements.txt (line 27))
  Downloading sarvamai-0.1.28-py3-none-any.whl.metadata (26 kB)
...
Collecting mariadb (from -r requirements.txt)
  Downloading mariadb-1.1.11.tar.gz (88 kB)
  Installing build dependencies ... -   done
  Getting requirements to build wheel ... -   error
  error: subprocess-exited-with-error
  
  × Getting requirements to build wheel did not run successfully.
  │ exit code: 1
  ╰─> [29 lines of output]
      /bin/sh: mariadb_config: command not found
      Traceback (most recent call last):
      ...
      OSError: mariadb_config not found.
      
      This error typically indicates that MariaDB Connector/C, a dependency which
      must be preinstalled, is not found.
      If MariaDB Connector/C is not installed, see installation instructions
      If MariaDB Connector/C is installed, either set the environment variable
      MARIADB_CONFIG or edit the configuration file 'site.cfg' to set the
       'mariadb_config' option to the file location of the mariadb_config utility.
      
      [end of output]
```
**Result:** The installation failed because the system is missing the MariaDB C connector (`mariadb_config not found`).

---

## 2. Docker Run Attempt
**Command:** `docker compose build`

**Output / Errors:**
```text
zsh:1: command not found: docker
```
**Result:** Docker is not installed on this machine, so the recommended Quickstart path failed.

---

## 3. README Review & Expected Workflow
**What the README says to do:**
The main `README.md` explicitly instructs users to configure via Docker:
1. `cp .env.example .env`
2. `docker compose build`
3. `docker compose up`

It also instructs users to configure XPaths for browser automation in `src/app/interface_manager/xpaths.json`. It does **not** mention `pip install -r requirements.txt` directly on the main page, though it links to a local/non-docker setup document deep in the docs folder (`docs/TDMS_and_Dashboard_ui/setup.md`).

---

## 4. Evaluation Checklist / Issue Radar

- **[x] Does pip install work cleanly?**
  No. It immediately fails building `mariadb` because it relies on a system-level C dependency (MariaDB Connector/C) which is missing.

- **[x] Does the README tell you clearly how to start?**
  Yes, but only for Docker users. If you try to run it locally with Python, the README buries those instructions in a sub-document and does not warn about system-level C dependencies.

- **[x] What input format does it expect?**
  It expects `.env` variables and `config.json` for application settings. For evaluation logic, it expects test data to be managed via its "TDMS" (Test Data Management System) and relies on `xpaths.json` for scraping/evaluating web interfaces.

- **[x] Can it actually hit an external API endpoint?**
  Yes. The architecture explicitly supports "API, web, and WhatsApp-style interfaces."

- **[x] What metrics does it claim to measure?**
  Based on scanning the `src/lib/strategy/` directory, it measures:
  - Similarity match
  - Internal Truth
  - Privacy
  - Safety
  - Hallucination
  - Fairness/Preference
  - Robustness (Out of Distribution / advGLUE)

- **[x] Are those metrics defined anywhere?**
  They are not explicitly defined or explained in the top-level README. You have to dig into the source code (`src/lib/strategy/`) or the documentation portal to find what they actually mean.

- **[x] Does it work with Gemini or only specific APIs?**
  Yes, it works with Gemini. Searching the codebase reveals explicit handlers for Gemini in `src/app/interface_manager/api_handler.py` and `src/lib/interface_manager/client.py`.

- **[x] Does it produce output you can actually interpret?**
  Because the tool crashed on installation, I couldn't generate output locally. However, based on the README, it claims to produce a Test Case Execution Dashboard with Timelines, Run Details, and Analysis graphs.

- **[x] Is there any safety/bias evaluation?**
  Yes, the codebase contains explicit evaluation strategies for this (`safety.py` and `fairness_preference.py`).

- **[x] When it breaks, are errors useful or cryptic?**
  The Python `pip install` error (`mariadb_config not found`) is somewhat cryptic for a general user, though it does explicitly state that the "MariaDB Connector/C, a dependency which must be preinstalled, is not found". The lack of a troubleshooting guide in the README makes this harder to resolve.
