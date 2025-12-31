# CLI Examples

Practical, copy-paste command examples. For full flags and options, see `docs/reference/CLI.md` or run `python -m cihub <command> --help`.

---

## Quickstart

```bash
# Scaffold a minimal repo and smoke test it
WORKDIR=$(mktemp -d)
python -m cihub scaffold python-pyproject "$WORKDIR/cihub-sample"
python -m cihub smoke "$WORKDIR/cihub-sample"

# Full smoke test (runs cihub ci)
python -m cihub smoke --full "$WORKDIR/cihub-sample"
```

---

## Repo Setup (Distributed Mode)

```bash
python -m cihub detect --repo /path/to/repo
python -m cihub init --repo /path/to/repo --apply
python -m cihub validate --repo /path/to/repo
```

Update workflow/config after changes:

```bash
python -m cihub update --repo /path/to/repo --apply
```

---

## Run CI Locally

```bash
python -m cihub ci --repo /path/to/repo --install-deps
python -m cihub run ruff --repo /path/to/repo
```

Outputs:

```bash
ls /path/to/repo/.cihub
cat /path/to/repo/.cihub/report.json
cat /path/to/repo/.cihub/summary.md
```

---

## Reports

```bash
python -m cihub report build --repo /path/to/repo
python -m cihub report summary --report /path/to/repo/.cihub/report.json
python -m cihub report outputs --report /path/to/repo/.cihub/report.json
python -m cihub report aggregate --dispatch-dir dispatch-artifacts --output hub-report.json
python -m cihub report aggregate --reports-dir reports --output hub-report.json
```

---

## Hub-Side Configs

Create a repo config:

```bash
python -m cihub new my-repo --owner my-org --language python
```

Inspect and edit:

```bash
python -m cihub config --repo my-repo show
python -m cihub config --repo my-repo set python.tools.pytest.threshold 80
python -m cihub config --repo my-repo enable bandit
python -m cihub config --repo my-repo disable mutmut
python -m cihub config --repo my-repo edit
```

Emit workflow outputs for Actions:

```bash
python -m cihub config-outputs --repo /path/to/repo --github-output
```

---

## Docs & ADRs

```bash
python -m cihub docs generate
python -m cihub docs check
python -m cihub docs links
python -m cihub docs links --external
```

```bash
python -m cihub adr list
python -m cihub adr new "Add new workflow policy"
python -m cihub adr check
```

---

## Secrets & Templates

```bash
python -m cihub setup-secrets --verify
python -m cihub setup-secrets --all
python -m cihub setup-nvd --verify
python -m cihub sync-templates --check
python -m cihub sync-templates --repo owner/name
```

---

## Java Helpers

```bash
python -m cihub fix-pom --repo /path/to/java-repo --apply
python -m cihub fix-deps --repo /path/to/java-repo --apply
```

---

## Hub CI Helpers

Use these to run hub checks locally (mirrors parts of hub-production CI):

```bash
python -m cihub hub-ci ruff --path .
python -m cihub hub-ci black --path .
python -m cihub hub-ci bandit --path .
python -m cihub hub-ci pip-audit --path .
python -m cihub hub-ci mutmut --workdir . --output-dir .cihub
python -m cihub hub-ci validate-configs
python -m cihub hub-ci validate-profiles
python -m cihub hub-ci license-check
```

Full list:

```bash
python -m cihub hub-ci --help
```

---

## Local Validation Wrapper

```bash
python -m cihub check
python -m cihub verify
python -m cihub verify --remote
python -m cihub verify --remote --integration --install-deps
make verify
```

Advanced options:

```bash
python -m cihub check --smoke-repo /path/to/repo --install-deps
python -m cihub check --relax --keep
```
