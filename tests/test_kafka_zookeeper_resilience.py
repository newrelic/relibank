import os
import time
from pathlib import Path

import pytest

try:
    import yaml
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    from kubernetes.stream import stream
    from kubernetes.stream.ws_client import ERROR_CHANNEL
    _KUBE_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - only hit if kubernetes isn't installed
    _KUBE_IMPORT_ERROR = exc


def load_env_from_skaffold():
    """Load environment variables from skaffold.env if present (local dev). Matches
    the identical helper in tests/test_db_pool_e2e.py."""
    skaffold_env = Path(__file__).parent.parent / "skaffold.env"
    if skaffold_env.exists():
        with open(skaffold_env) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val


load_env_from_skaffold()

TARGET_COLOR = os.getenv("TARGET_COLOR", "").strip()
NAMESPACE = f"relibank-{TARGET_COLOR}" if TARGET_COLOR else "relibank"
ALLOW_DISRUPTIVE = os.getenv("ALLOW_DISRUPTIVE_K8S_TESTS", "").strip().lower() == "true"

ZOOKEEPER_SELECTOR = "app=zookeeper"
KAFKA_SELECTOR = "app=kafka"
POD_READY_TIMEOUT_SEC = int(os.getenv("K8S_POD_READY_TIMEOUT_SEC", "180"))
POLL_INTERVAL_SEC = 5


def _load_kube_config() -> bool:
    """Mirrors scenario_service.py's own in-cluster/kubeconfig fallback exactly."""
    try:
        config.load_incluster_config()
        return True
    except Exception:
        pass
    try:
        config.load_kube_config()
        return True
    except Exception:
        return False


_KUBE_AVAILABLE = _KUBE_IMPORT_ERROR is None and _load_kube_config()

pytestmark = [
    pytest.mark.skipif(
        not _KUBE_AVAILABLE,
        reason=(
            "No usable Kubernetes context (in-cluster or ~/.kube/config). Expected "
            "on the legacy 'events' env and on contributor laptops without cluster "
            "access; NOT expected on sandbox/staging/prod AKS-backed CI runs -- if "
            "this skips there, treat it as a CI wiring bug, not a pass."
        ),
    ),
    pytest.mark.timeout(300),
]


def _core_v1():
    return client.CoreV1Api()


def _active_color() -> str:
    """Reads the live main-ingress backend -- the same ground truth test-suite.yml's
    own 'Resolve effective color' step uses (kubectl get ingress main-ingress -n
    default -o jsonpath='{.spec.rules[0].http.paths[0].backend.service.name}')."""
    ingress = client.NetworkingV1Api().read_namespaced_ingress("main-ingress", "default")
    backend_service = ingress.spec.rules[0].http.paths[0].backend.service.name  # "blue-service"/"green-service"
    return backend_service.removesuffix("-service")


def _disruptive_tests_allowed() -> tuple[bool, str]:
    if not ALLOW_DISRUPTIVE:
        return False, "ALLOW_DISRUPTIVE_K8S_TESTS is not 'true' -- pod-killing tests are opt-in only."
    if not TARGET_COLOR:
        return False, (
            "TARGET_COLOR is not set -- refusing to run pod-killing tests against an "
            "implicit/active color. Set TARGET_COLOR explicitly, even in sandbox/staging."
        )
    try:
        active = _active_color()
    except Exception as exc:
        return False, f"Could not verify the live ingress's active color ({exc}); refusing to guess."
    if TARGET_COLOR == active:
        return False, (
            f"TARGET_COLOR={TARGET_COLOR!r} matches the color main-ingress is currently "
            f"routing default traffic to ({active!r}) -- refusing to kill its zookeeper "
            "pod. Target the inactive/canary color instead."
        )
    return True, ""


_disruptive_ok, _disruptive_reason = _disruptive_tests_allowed()
_disruptive = pytest.mark.skipif(not _disruptive_ok, reason=_disruptive_reason)


def _get_pod(label_selector: str):
    pods = _core_v1().list_namespaced_pod(namespace=NAMESPACE, label_selector=label_selector)
    assert pods.items, f"No pod found for selector '{label_selector}' in namespace '{NAMESPACE}'"
    return pods.items[0]


def _wait_for_ready_pod(label_selector: str, exclude_pod_name: str = None, timeout: int = POD_READY_TIMEOUT_SEC):
    """Polls until a pod matching label_selector (other than exclude_pod_name, if
    given) reports phase=Running and condition Ready=True. Returns the pod object."""
    deadline = time.time() + timeout
    last_seen = None
    while time.time() < deadline:
        pods = _core_v1().list_namespaced_pod(namespace=NAMESPACE, label_selector=label_selector)
        for pod in pods.items:
            if exclude_pod_name and pod.metadata.name == exclude_pod_name:
                continue
            last_seen = pod
            conditions = {c.type: c.status for c in (pod.status.conditions or [])}
            if pod.status.phase == "Running" and conditions.get("Ready") == "True":
                return pod
        time.sleep(POLL_INTERVAL_SEC)
    pytest.fail(
        f"No ready pod for selector '{label_selector}' in '{NAMESPACE}' within {timeout}s "
        f"(last seen: {getattr(last_seen.metadata, 'name', None) if last_seen else None}, "
        f"phase={getattr(last_seen.status, 'phase', None) if last_seen else None})"
    )


def _exec_in_pod(pod_name: str, container: str, command: list, timeout: int = 15) -> tuple[str, int | None]:
    """Runs `command` inside a pod/container via the exec subresource -- the
    API-level equivalent of `kubectl exec` -- and returns (combined_output, exit_code).

    exit_code is None if the websocket closed without ever delivering a status frame on
    the error channel -- a real race in the kubernetes client's WSClient over
    higher-latency connections (seen in CI, not reproduced against a local cluster): its own
    `.returncode` property crashes with `TypeError: 'NoneType' object is not subscriptable`
    in exactly this case, so we parse the same channel ourselves and treat "no status frame"
    as "unknown" rather than blowing up. Callers must treat None as inconclusive (retry),
    not as a specific exit code.
    """
    ws = stream(
        _core_v1().connect_get_namespaced_pod_exec,
        name=pod_name,
        namespace=NAMESPACE,
        container=container,
        command=command,
        stderr=True, stdin=False, stdout=True, tty=False,
        _preload_content=False,
    )
    ws.run_forever(timeout=timeout)
    output = ws.read_all()
    err_raw = ws.read_channel(ERROR_CHANNEL)
    err = yaml.safe_load(err_raw) if err_raw else None
    if err is None:
        exit_code = None
    elif err.get("status") == "Success":
        exit_code = 0
    else:
        exit_code = int(err["details"]["causes"][0]["message"])
    ws.close()
    return output, exit_code


# --- (a) PVC exists and is bound -----------------------------------------------

def test_zookeeper_pvc_exists_and_bound():
    """
    Verifies Fix 1's zookeeper-data PVC exists and is Bound -- i.e. Zookeeper's
    state now survives pod rescheduling, instead of starting from empty state
    the way it did on the Sept 20 AKS node image upgrade that triggered the
    incident (Zookeeper had no PVC at all).
    """
    v1 = _core_v1()
    try:
        pvc = v1.read_namespaced_persistent_volume_claim(name="zookeeper-data", namespace=NAMESPACE)
    except ApiException as exc:
        if exc.status == 404:
            pytest.fail(
                f"PersistentVolumeClaim 'zookeeper-data' not found in '{NAMESPACE}' -- "
                "Fix 1 (Zookeeper PVC) has not been applied to this environment/color yet."
            )
        raise
    assert pvc.status.phase == "Bound", (
        f"zookeeper-data PVC exists but is not Bound (phase={pvc.status.phase}) -- "
        "check the cluster's default StorageClass / dynamic provisioning."
    )
    assert pvc.spec.access_modes == ["ReadWriteOnce"]


# --- (b) pod delete -> data intact, kafka rejoins ------------------------------

@_disruptive
def test_zookeeper_survives_pod_delete_with_data_intact():
    """
    Reproduces the incident's actual mechanism at pod-restart granularity: delete
    the running Zookeeper pod (the same effect the Sept 20 node image upgrade's
    reschedule had), wait for the Deployment to replace it, and confirm:
      1. the replacement reports `imok` to `ruok` (the incident doc's own manual
         verification step), and
      2. Kafka actually rejoins with a working session -- not just "the
         zookeeper process came back", but specifically that Kafka's logs stop
         showing the "client must try another server" loop the incident found.
    """
    old_pod = _get_pod(ZOOKEEPER_SELECTOR)
    old_name = old_pod.metadata.name

    _core_v1().delete_namespaced_pod(name=old_name, namespace=NAMESPACE)

    new_pod = _wait_for_ready_pod(ZOOKEEPER_SELECTOR, exclude_pod_name=old_name)
    assert new_pod.metadata.name != old_name, "Deployment did not replace the deleted pod"

    ruok_output, _ = _exec_in_pod(
        new_pod.metadata.name, "zookeeper",
        ["/bin/bash", "-c", "echo ruok | timeout 2 nc -w 2 localhost 2181"],
    )
    assert "imok" in ruok_output, f"zookeeper did not report imok after restart: {ruok_output!r}"

    kafka_pod = _get_pod(KAFKA_SELECTOR)
    deadline = time.time() + 120
    last_logs = ""
    while time.time() < deadline:
        last_logs = _core_v1().read_namespaced_pod_log(
            name=kafka_pod.metadata.name, namespace=NAMESPACE, container="kafka", tail_lines=200,
        )
        if "client must try another server" in last_logs or "EndOfStreamException" in last_logs:
            time.sleep(POLL_INTERVAL_SEC)
            continue
        break
    assert "client must try another server" not in last_logs, (
        "Kafka is still stuck in the incident's session-deadlock loop after the "
        f"zookeeper restart:\n{last_logs[-1000:]}"
    )


# There is deliberately no test asserting that Kafka's readiness probe
# (kafka-broker-api-versions.sh) detects a broken Zookeeper session. Verified
# empirically -- both by deleting Zookeeper's pod and by a controlled SIGSTOP
# freeze of the Zookeeper process lasting 47s -- that it never fails during a
# Zookeeper outage: Kafka answers it (and kafka-topics.sh --list) from local
# broker state without needing an active Zookeeper session. So "the probe would
# fail" is not something this probe can prove; a test asserting it would fail
# every run, on a false premise, not on flakiness. See docs/PROD_BLUE_KAFKA_ZOOKEEPER_INCIDENT.md
# Fix 1 and docs/KAFKA_ZOOKEEPER_RESILIENCE_TESTING_STRATEGY.md for the writeup.


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
