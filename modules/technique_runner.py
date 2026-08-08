"""Discover, execute, and report on OCI attack-technique test scenarios.

Each technique lives in ``techniques/<folder_name>/`` and contains:

- ``tech-<Id>.yaml`` with metadata
- ``terraform/`` with infrastructure to provision the attack scenario
- ``test.py`` that executes the attack and writes evidence

The runner orchestrates: terraform apply → test.py → evidence → terraform destroy.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------

class ProgressCallback(Protocol):
    """Signature for progress callbacks.

    *phase* is one of ``init``, ``apply``, ``test``, ``destroy``.
    *message* is a human-readable status line (may contain ANSI codes from
    terraform).  When *done* is ``True`` the phase has completed.
    """

    def __call__(
        self, *, phase: str, message: str, done: bool = False
    ) -> None: ...


def _noop_progress(*, phase: str, message: str, done: bool = False) -> None:
    pass

# ---------------------------------------------------------------------------
# Category inference
# ---------------------------------------------------------------------------

_CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["function"], "functions"),
    (["container", "image"], "container"),
    (["object_storage", "preauthenticated"], "storage"),
    (["vault", "secret", "kms"], "vault"),
    (["instance", "console_connection"], "compute"),
    (["user", "api_key", "policy", "principal", "password"], "iam"),
]


def _infer_category(folder_name: str) -> str:
    lower = folder_name.lower()
    for keywords, cat in _CATEGORY_RULES:
        if any(kw in lower for kw in keywords):
            return cat
    return "other"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class TechniqueInfo:
    """Metadata for a discovered technique."""

    name: str
    path: Path
    category: str
    has_terraform: bool
    has_test: bool
    yaml_path: Path
    yaml_data: dict[str, Any]


@dataclasses.dataclass
class TechniqueResult:
    """Outcome of running a single technique test."""

    technique: str
    category: str
    status: str  # PASS | FAIL | SKIP | ERROR
    message: str
    timestamp: str = dataclasses.field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evidence: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_techniques(
    root: Path,
    *,
    category: str | None = None,
    name: str | None = None,
) -> list[TechniqueInfo]:
    """Scan *root* for technique directories and return matching :class:`TechniqueInfo` objects.

    A directory is a technique if it contains at least one ``tech-*.yaml`` file.
    """
    techniques: list[TechniqueInfo] = []

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue

        yamls = list(child.glob("tech-*.yaml"))
        if not yamls:
            continue

        yaml_path = yamls[0]
        try:
            yaml_data = yaml.safe_load(yaml_path.read_text()) or {}
        except Exception as exc:
            log.warning("Skipping %s: cannot parse YAML: %s", child.name, exc)
            continue

        tf_dir = child / "terraform"
        test_py = child / "test.py"

        info = TechniqueInfo(
            name=child.name,
            path=child,
            category=_infer_category(child.name),
            has_terraform=tf_dir.is_dir()
            and any(tf_dir.glob("*.tf")),
            has_test=test_py.is_file() and test_py.stat().st_size > 0,
            yaml_path=yaml_path,
            yaml_data=yaml_data,
        )

        if name and info.name != name:
            continue
        if category and info.category != category:
            continue

        techniques.append(info)

    return techniques


# ---------------------------------------------------------------------------
# Terraform helpers
# ---------------------------------------------------------------------------

_TERRAFORM = shutil.which("terraform") or "terraform"


def _run_tf(
    args: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    capture: bool = False,
    on_output: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a terraform command.

    When *on_output* is provided the process streams stdout/stderr line-by-line
    through the callback **and** captures the full output for the return value.
    """
    cmd = [_TERRAFORM, *args]
    merged_env = {**os.environ, **(env or {})}

    if on_output is None:
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            capture_output=capture,
            text=True,
            timeout=600,
        )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def _drain(stream, bucket):
        assert stream is not None
        for line in stream:
            bucket.append(line)
            on_output(line.rstrip("\n"))

    stderr_thread = threading.Thread(
        target=_drain, args=(proc.stderr, stderr_lines), daemon=True
    )
    stderr_thread.start()
    _drain(proc.stdout, stdout_lines)
    stderr_thread.join(timeout=10)
    proc.wait(timeout=600)

    return subprocess.CompletedProcess(
        cmd,
        proc.returncode,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
    )


def _tf_init(
    tf_dir: Path,
    *,
    on_output: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    lockfile = tf_dir / ".terraform.lock.hcl"
    providers = tf_dir / ".terraform" / "providers"
    already_initialised = lockfile.exists() and providers.is_dir()

    env: dict[str, str] = {"CHECKPOINT_DISABLE": "1"}
    args = ["init", "-input=false"]
    if already_initialised:
        args.extend(["-plugin-dir", str(providers.resolve())])

    proc = _run_tf(args, tf_dir, capture=True, env=env, on_output=on_output)
    if proc.returncode != 0 and already_initialised:
        log.warning("Offline init (-plugin-dir) failed, retrying with registry …")
        return _run_tf(
            ["init", "-input=false"], tf_dir, capture=True, env=env,
            on_output=on_output,
        )
    return proc


def _tf_apply(
    tf_dir: Path,
    var_file: Path,
    *,
    on_output: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    return _run_tf(
        ["apply", "-auto-approve", "-input=false", f"-var-file={var_file}"],
        tf_dir,
        capture=True,
        on_output=on_output,
    )


def _tf_output(tf_dir: Path) -> dict[str, Any]:
    proc = _run_tf(["output", "-json"], tf_dir, capture=True)
    if proc.returncode != 0:
        return {}
    raw = json.loads(proc.stdout)
    return {k: v.get("value") for k, v in raw.items()}


def _tf_destroy(
    tf_dir: Path,
    var_file: Path,
    *,
    on_output: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    return _run_tf(
        ["destroy", "-auto-approve", "-input=false", f"-var-file={var_file}"],
        tf_dir,
        capture=True,
        on_output=on_output,
    )


# ---------------------------------------------------------------------------
# Test execution
# ---------------------------------------------------------------------------


def _write_oci_config(
    outputs: dict[str, Any], tmpdir: Path
) -> tuple[Path, Path] | None:
    """Write a temporary OCI config + private key from Terraform outputs.

    Returns ``(config_path, key_path)`` or *None* if outputs are incomplete.
    """
    required = ("oci_config_snippet", "private_key_pem")
    if not all(outputs.get(k) for k in required):
        return None

    key_path = tmpdir / "private_key.pem"
    key_path.write_text(outputs["private_key_pem"])
    key_path.chmod(0o600)

    config_text = outputs["oci_config_snippet"].replace(
        "<path_to_private_key>", str(key_path)
    )
    config_path = tmpdir / "config"
    config_path.write_text(config_text)
    config_path.chmod(0o600)

    return config_path, key_path


@dataclasses.dataclass
class _TestOutput:
    """Raw output captured from a test.py execution."""
    result: TechniqueResult
    stdout: str = ""
    stderr: str = ""


def _run_test(
    technique: TechniqueInfo,
    outputs: dict[str, Any],
    tmpdir: Path,
) -> _TestOutput:
    """Execute the technique's ``test.py`` and return result + captured output."""
    test_py = technique.path / "test.py"

    env = {
        **os.environ,
        "TECHNIQUE_NAME": technique.name,
        "TECHNIQUE_DIR": str(technique.path),
        "TF_OUTPUTS": json.dumps(outputs),
    }

    oci_paths = _write_oci_config(outputs, tmpdir)
    if oci_paths:
        config_path, _ = oci_paths
        env["OCI_CLI_CONFIG_FILE"] = str(config_path)
        env["OCI_CONFIG_FILE"] = str(config_path)

    for key, value in outputs.items():
        env_key = f"TF_{key.upper()}"
        if isinstance(value, str):
            env[env_key] = value

    try:
        proc = subprocess.run(
            [sys.executable, str(test_py)],
            cwd=technique.path,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return _TestOutput(
            result=TechniqueResult(
                technique=technique.name,
                category=technique.category,
                status="ERROR",
                message="test.py timed out after 600s",
            ),
        )
    except Exception as exc:
        return _TestOutput(
            result=TechniqueResult(
                technique=technique.name,
                category=technique.category,
                status="ERROR",
                message=f"test.py execution error: {exc}",
            ),
        )

    evidence_path = technique.path / "last_evidence.json"
    evidence: dict[str, Any] | None = None
    if evidence_path.exists():
        try:
            evidence = json.loads(evidence_path.read_text())
        except Exception:
            pass

    if evidence and "status" in evidence:
        return _TestOutput(
            result=TechniqueResult(
                technique=technique.name,
                category=technique.category,
                status=evidence["status"],
                message=evidence.get("message", ""),
                timestamp=evidence.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                evidence=evidence.get("evidence"),
            ),
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    if proc.returncode == 0:
        return _TestOutput(
            result=TechniqueResult(
                technique=technique.name,
                category=technique.category,
                status="PASS",
                message=proc.stdout.strip()[:500] or "test.py exited 0",
                evidence=evidence.get("evidence") if evidence else None,
            ),
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    return _TestOutput(
        result=TechniqueResult(
            technique=technique.name,
            category=technique.category,
            status="FAIL",
            message=(proc.stderr.strip() or proc.stdout.strip())[:500]
            or f"test.py exited {proc.returncode}",
        ),
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


# ---------------------------------------------------------------------------
# Post-failure diagnostics
# ---------------------------------------------------------------------------


def _collect_diagnostics(
    technique: TechniqueInfo,
    outputs: dict[str, Any],
    tmpdir: Path,
    result: TechniqueResult,
    test_stdout: str,
    test_stderr: str,
) -> Path | None:
    """Collect diagnostic data about deployed resources after a test failure.

    Runs between the test phase and the destroy phase so the infrastructure
    is still live. Returns the path to the diagnostics directory, or None on
    error.
    """
    diag_dir = technique.path / "diagnostics"
    try:
        diag_dir.mkdir(exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = diag_dir / ts
        run_dir.mkdir(exist_ok=True)

        # 1. Save test stdout/stderr
        (run_dir / "test_stdout.txt").write_text(test_stdout or "(empty)")
        (run_dir / "test_stderr.txt").write_text(test_stderr or "(empty)")

        # 2. Save terraform outputs (non-sensitive)
        safe_outputs = {
            k: v for k, v in outputs.items()
            if k not in ("private_key_pem", "auth_token", "oci_config_snippet")
        }
        (run_dir / "terraform_outputs.json").write_text(
            json.dumps(safe_outputs, indent=2)
        )

        # 3. Terraform state list -- what resources exist?
        tf_dir = technique.path / "terraform"
        state_proc = _run_tf(["state", "list"], tf_dir, capture=True)
        (run_dir / "terraform_state_list.txt").write_text(
            state_proc.stdout if state_proc.returncode == 0 else
            f"(state list failed: {state_proc.stderr})"
        )

        # 4. Query key resources via the attacker's OCI CLI config
        oci_config = tmpdir / "config"
        if oci_config.exists():
            oci_env = {
                **os.environ,
                "OCI_CLI_CONFIG_FILE": str(oci_config),
                "OCI_CONFIG_FILE": str(oci_config),
                "SUPPRESS_LABEL_WARNING": "True",
            }
            probes: list[dict[str, Any]] = []

            # Probe IAM identity of the attacker
            probe = _run_oci_probe(
                ["iam", "user", "get", "--user-id",
                 outputs.get("attacker_user_ocid", "MISSING")],
                oci_env,
            )
            probes.append({"probe": "iam_user_get", **probe})

            # If there's a compartment, list recent audit events
            compartment = outputs.get("compartment_ocid", "")
            if compartment:
                probe = _run_oci_probe(
                    ["iam", "policy", "list",
                     "--compartment-id", compartment,
                     "--limit", "5"],
                    oci_env,
                )
                probes.append({"probe": "iam_policy_list", **probe})

            (run_dir / "oci_probes.json").write_text(
                json.dumps(probes, indent=2)
            )

        # 5. Save the evidence file and result summary
        (run_dir / "result.json").write_text(
            json.dumps(dataclasses.asdict(result), indent=2)
        )

        log.info("Diagnostics saved to %s", run_dir)
        return run_dir

    except Exception as exc:
        log.warning("Failed to collect diagnostics: %s", exc)
        return None


def _run_oci_probe(
    args: list[str], env: dict[str, str]
) -> dict[str, Any]:
    """Run an OCI CLI command as a diagnostic probe.

    Returns a dict with ``rc``, ``stdout`` (truncated), and ``stderr``
    (truncated). Never raises.
    """
    try:
        proc = subprocess.run(
            ["oci", *args],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        return {
            "rc": proc.returncode,
            "stdout": proc.stdout[:2000],
            "stderr": proc.stderr[:2000],
        }
    except Exception as exc:
        return {"rc": -1, "stdout": "", "stderr": str(exc)[:500]}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_technique(
    technique: TechniqueInfo,
    shared_vars: dict[str, Any],
    *,
    destroy: bool = True,
    results_dir: Path | None = None,
    progress: ProgressCallback | None = None,
) -> TechniqueResult:
    """Provision, test, and (optionally) tear down a single technique."""
    _progress = progress or _noop_progress
    tf_dir = technique.path / "terraform"

    if not technique.has_terraform:
        return TechniqueResult(
            technique=technique.name,
            category=technique.category,
            status="SKIP",
            message="No Terraform configuration found",
        )

    if not technique.has_test:
        return TechniqueResult(
            technique=technique.name,
            category=technique.category,
            status="SKIP",
            message="test.py is missing or empty",
        )

    def _phase_output(phase: str):
        """Return a callback that forwards terraform output lines."""
        def _cb(line: str) -> None:
            _progress(phase=phase, message=line)
        return _cb

    with tempfile.TemporaryDirectory(prefix=f"polici-{technique.name}-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        var_file = tmpdir / "shared.tfvars.json"
        var_file.write_text(json.dumps(shared_vars))

        # --- init ---
        _progress(phase="init", message="Initialising Terraform providers …")
        t0 = time.monotonic()
        proc = _tf_init(tf_dir, on_output=_phase_output("init"))
        elapsed = time.monotonic() - t0
        if proc.returncode != 0:
            _progress(phase="init", message=f"FAILED ({elapsed:.0f}s)", done=True)
            return TechniqueResult(
                technique=technique.name,
                category=technique.category,
                status="ERROR",
                message=f"terraform init failed: {(proc.stderr or proc.stdout)[:800]}",
            )
        _progress(phase="init", message=f"Done ({elapsed:.0f}s)", done=True)

        # --- apply ---
        _progress(phase="apply", message="Creating infrastructure …")
        t0 = time.monotonic()
        proc = _tf_apply(tf_dir, var_file, on_output=_phase_output("apply"))
        elapsed = time.monotonic() - t0
        if proc.returncode != 0:
            _progress(phase="apply", message=f"FAILED ({elapsed:.0f}s)", done=True)
            return TechniqueResult(
                technique=technique.name,
                category=technique.category,
                status="ERROR",
                message=f"terraform apply failed: {(proc.stderr or proc.stdout)[:800]}",
            )
        _progress(phase="apply", message=f"Done ({elapsed:.0f}s)", done=True)

        outputs = _tf_output(tf_dir)

        # --- test ---
        _progress(phase="test", message="Running attack test …")
        t0 = time.monotonic()
        test_output = _run_test(technique, outputs, tmpdir)
        result = test_output.result
        elapsed = time.monotonic() - t0
        _progress(
            phase="test",
            message=f"{result.status} ({elapsed:.0f}s)",
            done=True,
        )

        # --- persist result ---
        result_dict = dataclasses.asdict(result)
        if results_dir:
            results_dir.mkdir(parents=True, exist_ok=True)
            result_file = results_dir / f"{technique.name}.json"
            result_file.write_text(json.dumps(result_dict, indent=2))

        evidence_path = technique.path / "last_evidence.json"
        evidence_path.write_text(json.dumps(result_dict, indent=2))

        # --- diagnostics on failure ---
        if result.status in ("FAIL", "ERROR"):
            _progress(phase="diagnostics", message="Collecting diagnostic data …")
            diag_path = _collect_diagnostics(
                technique, outputs, tmpdir, result,
                test_output.stdout, test_output.stderr,
            )
            if diag_path:
                _progress(
                    phase="diagnostics",
                    message=f"Saved to {diag_path.relative_to(technique.path)}",
                    done=True,
                )
            else:
                _progress(
                    phase="diagnostics",
                    message="Collection failed",
                    done=True,
                )

        # --- destroy ---
        if destroy:
            _progress(phase="destroy", message="Tearing down infrastructure …")
            t0 = time.monotonic()
            _tf_destroy(tf_dir, var_file, on_output=_phase_output("destroy"))
            elapsed = time.monotonic() - t0
            _progress(phase="destroy", message=f"Done ({elapsed:.0f}s)", done=True)

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_results(results: list[TechniqueResult]) -> None:
    """Print a summary table of technique test results."""
    if not results:
        return

    status_icons = {
        "PASS": "✓",
        "FAIL": "✗",
        "SKIP": "—",
        "ERROR": "!",
    }

    print(f"\n{'':>2}{'TECHNIQUE':<50}  {'CATEGORY':<10}  RESULT")
    print("  " + "-" * 72)

    for r in results:
        icon = status_icons.get(r.status, "?")
        msg_suffix = f"  {r.message[:60]}" if r.message else ""
        print(f"  {r.technique:<50}  {r.category:<10}  {icon} {r.status}{msg_suffix}")

    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    errors = sum(1 for r in results if r.status == "ERROR")
    skipped = sum(1 for r in results if r.status == "SKIP")

    print(f"\n  {total} technique(s): {passed} passed, {failed} failed, {errors} error(s), {skipped} skipped\n")
