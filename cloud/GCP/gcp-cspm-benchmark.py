"""
gcp-cspm-benchmark.py

Assists with provisioning calculations by retrieving a count
of all billable resources attached to a GCP project.
"""

import argparse
import csv
import logging
import os
from functools import cached_property
from typing import List, Dict, Any
from tabulate import tabulate
import google.api_core.exceptions
from google.cloud.resourcemanager import ProjectsClient
from google.cloud.resourcemanager_v3.types import Project
from google.cloud import compute
from googleapiclient import discovery
from googleapiclient.errors import HttpError

# Suppress gRPC and absl logs
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Configuration for logging
LOG_LEVEL = logging.DEBUG
log = logging.getLogger("gcp")
log.setLevel(LOG_LEVEL)
ch = logging.StreamHandler()
ch.setLevel(LOG_LEVEL)
formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")
ch.setFormatter(formatter)
log.addHandler(ch)


def parse_arguments():
    """Parse command line arguments for subset processing."""
    parser = argparse.ArgumentParser(
        description="Process GCP projects in sequential subsets for provisioning calculations"
    )
    parser.add_argument(
        "--subset-size", "-m",
        type=int,
        required=True,
        help="Number of projects per subset (M)"
    )
    parser.add_argument(
        "--subset-index", "-n",
        type=int,
        required=True,
        help="Index of the subset to process (0-based, N)"
    )
    parser.add_argument(
        "--output-prefix", "-o",
        type=str,
        default="gcp-benchmark",
        help="Prefix for output files (default: gcp-benchmark)"
    )
    return parser.parse_args()


def get_project_subset(projects: List[Project], subset_size: int, subset_index: int) -> List[Project]:
    """
    Extract a sequential subset of projects.
    
    Args:
        projects: List of all projects
        subset_size: Number of projects per subset (M)
        subset_index: Index of the subset to process (0-based, N)
    
    Returns:
        List of projects for the specified subset
    """
    total_projects = len(projects)
    start_index = subset_index * subset_size
    end_index = min(start_index + subset_size, total_projects)
    
    if start_index >= total_projects:
        log.warning(
            "Subset index %d is out of range. Total projects: %d, subset size: %d",
            subset_index, total_projects, subset_size
        )
        return []
    
    subset = projects[start_index:end_index]
    log.info(
        "Processing subset %d: projects %d-%d of %d total projects (%d projects in this subset)",
        subset_index, start_index + 1, end_index, total_projects, len(subset)
    )
    
    return subset


class GCP:
    def projects(self) -> List[Project]:
        return list(ProjectsClient().search_projects())

    def list_instances(self, project_id: str):
        request = compute.AggregatedListInstancesRequest(max_results=50, project=project_id)
        return self.instances_client.aggregated_list(request=request)

    def clusters(self, project_id: str) -> List[Dict[str, Any]]:
        service = discovery.build("container", "v1")
        endpoint = service.projects().zones().clusters()  # pylint: disable=no-member
        request = endpoint.list(projectId=project_id, zone="-")
        response = request.execute()
        return response.get("clusters", [])

    def list_cloud_run_services(self, project_id: str) -> List[Dict[str, Any]]:
        service = discovery.build("run", "v1")
        parent = f"projects/{project_id}/locations/-"
        request = service.projects().locations().services().list(parent=parent)  # pylint: disable=no-member
        response = request.execute()
        return response.get("items", [])

    def list_cloud_run_jobs(self, project_id: str) -> List[Dict[str, Any]]:
        service = discovery.build("run", "v1")
        parent = f"namespaces/{project_id}"
        request = service.namespaces().jobs().list(parent=parent)  # pylint: disable=no-member
        response = request.execute()
        return response.get("items", [])

    @cached_property
    def instances_client(self) -> compute.InstancesClient:
        return compute.InstancesClient()

    @classmethod
    def is_vm_kubenode(cls, instance: compute.Instance) -> bool:
        if any(k.key == "kubeconfig" for k in instance.metadata.items):
            return True

        if instance.labels:
            gke_indicators = ["goog-gke-node", "gke-cluster", "k8s-", "kubernetes"]
            for key, _ in instance.labels.items():
                if any(indicator in key.lower() for indicator in gke_indicators):
                    return True

        if instance.name and "gke-" in instance.name:
            return True

        return False

    @classmethod
    def is_vm_running(cls, instance: compute.Instance) -> bool:
        return instance.status != "TERMINATED"

    @classmethod
    def is_cluster_autopilot(cls, cluster: Dict[str, Any]) -> bool:
        return cluster.get("autopilot", {}).get("enabled", False)

    @classmethod
    def get_autopilot_active_nodes(cls, cluster: Dict[str, Any]) -> int:
        return cluster.get("currentNodeCount", 0)


def process_gcp_project(gcp_project: Project) -> Dict[str, Any]:
    if gcp_project.state == Project.State.DELETE_REQUESTED:
        log.info("Skipping GCP project %s (project pending deletion)", gcp_project.display_name)
        return {}

    result = {
        "project_id": gcp_project.project_id,
        "kubenodes_running": 0,
        "kubenodes_terminated": 0,
        "vms_running": 0,
        "vms_terminated": 0,
        "autopilot_clusters": 0,
        "autopilot_nodes": 0,
        "cloud_run_services": 0,
        "cloud_run_jobs": 0,
    }

    log.info("Processing GCP project: %s", gcp_project.display_name)

    fail_safe(count_instances, gcp_project, result)
    fail_safe(count_autopilot_clusters, gcp_project, result)
    fail_safe(count_cloud_run_services, gcp_project, result)
    fail_safe(count_cloud_run_jobs, gcp_project, result)
    fail_safe(validate_and_adjust_kube_counts, gcp_project, result)

    return result


def fail_safe(count_func, *args) -> None:
    try:
        count_func(*args)
    except google.api_core.exceptions.Forbidden as exc:
        if "Compute Engine API has not been used" in str(exc):
            log_warning("compute.googleapis.com", project.display_name)
            add_message(project.project_id, exc.errors[0]["message"])
        else:
            log.error("Unexpected error for project: %s: %s", project.display_name, exc)
    except HttpError as exc:
        if exc.status_code == 403 and "SERVICE_DISABLED" in str(exc):
            log_warning(get_service_disabled_name(exc), project.display_name)
            add_message(project.project_id, exc.reason)
        else:
            log.error("Unexpected error for project: %s: %s", project.display_name, exc)
    except Exception as exc:  # pylint: disable=broad-except
        log.error("Unexpected error for project: %s: %s", project.display_name, exc)


def log_warning(api: str, project_name: str) -> None:
    api_names = {
        "compute.googleapis.com": "Compute Engine",
        "container.googleapis.com": "Kubernetes Engine",
        "run.googleapis.com": "Cloud Run",
    }
    message = f"Unable to process {api_names[api]} API for project: {project_name}."
    log.warning(message)


def add_message(project_id: str, message: str) -> None:
    if project_id not in service_disabled_calls:
        service_disabled_calls[project_id] = []
    service_disabled_calls[project_id].append(message)


def get_service_disabled_name(exc: HttpError) -> str:
    for detail in exc.error_details:
        if detail.get("@type") == "type.googleapis.com/google.rpc.ErrorInfo":
            return detail["metadata"]["service"]
    return None


def validate_and_adjust_kube_counts(gcp_project: Project, result: Dict[str, Any]) -> None:
    """Compare instance-detected kube nodes with GKE API reported nodes and adjust if needed."""
    try:
        if gcp_project.project_id in service_disabled_calls:
            api_errors = service_disabled_calls[gcp_project.project_id]
            if any("container" in err.lower() for err in api_errors):
                message = (
                    f"Skipping validation for project {gcp_project.project_id} due to container API access issues"
                )
                log.debug(message)
                return

        standard_node_count = 0
        for cluster in gcp.clusters(gcp_project.project_id):
            if not GCP.is_cluster_autopilot(cluster):
                standard_node_count += cluster.get("currentNodeCount", 0)

        detected_nodes = result["kubenodes_running"]

        if standard_node_count > detected_nodes:
            discrepancy = standard_node_count - detected_nodes
            message = (
                f"Project {gcp_project.project_id}: GKE API reports {standard_node_count} nodes, "
                f"but only {detected_nodes} were detected via instance metadata. "
                f"Adjusting count to {standard_node_count} (added {discrepancy} nodes)"
            )
            log.warning(message)

            result["kubenodes_running"] = standard_node_count

    except Exception as e:  # pylint: disable=broad-except
        message = f"Error validating node counts for project {gcp_project.project_id}: {str(e)}"
        log.error(message)


def count_autopilot_clusters(gcp_project: Project, result: Dict[str, int]):
    for cluster in gcp.clusters(gcp_project.project_id):
        if GCP.is_cluster_autopilot(cluster):
            result["autopilot_clusters"] += 1
            result["autopilot_nodes"] += GCP.get_autopilot_active_nodes(cluster)


def count_instances(gcp_project: Project, result: Dict[str, int]):
    for _zone, response in gcp.list_instances(gcp_project.project_id):
        if response.instances:
            for instance in response.instances:
                typ = "kubenode" if GCP.is_vm_kubenode(instance) else "vm"
                state = "running" if GCP.is_vm_running(instance) else "terminated"
                key = f"{typ}s_{state}"
                result[key] += 1


def count_cloud_run_services(gcp_project: Project, result: Dict[str, int]):
    services = gcp.list_cloud_run_services(gcp_project.project_id)
    result["cloud_run_services"] = len(services)


def count_cloud_run_jobs(gcp_project: Project, result: Dict[str, int]):
    jobs = gcp.list_cloud_run_jobs(gcp_project.project_id)
    result["cloud_run_jobs"] = len(jobs)


def main():
    args = parse_arguments()
    
    global data, service_disabled_calls, gcp, project
    
    data = []
    service_disabled_calls = {}
    headers = {
        "project_id": "Project ID",
        "kubenodes_running": "K8s Nodes (Running)",
        "kubenodes_terminated": "K8s Nodes (Terminated)",
        "vms_running": "VMs (Running)",
        "vms_terminated": "VMs (Terminated)",
        "autopilot_clusters": "Autopilot Clusters",
        "autopilot_nodes": "Autopilot Nodes (Running)",
        "cloud_run_services": "Cloud Run Services",
        "cloud_run_jobs": "Cloud Run Jobs",
    }
    totals = {
        "project_id": f"subset_{args.subset_index}_totals",
        "kubenodes_running": 0,
        "kubenodes_terminated": 0,
        "vms_running": 0,
        "vms_terminated": 0,
        "autopilot_clusters": 0,
        "autopilot_nodes": 0,
        "cloud_run_services": 0,
        "cloud_run_jobs": 0,
    }

    gcp = GCP()

    # Get all projects and extract the subset
    all_projects = gcp.projects()
    if not all_projects:
        log.error("No GCP projects found")
        exit(1)  # pylint: disable=consider-using-sys-exit

    projects_subset = get_project_subset(all_projects, args.subset_size, args.subset_index)
    if not projects_subset:
        log.error("No projects in the specified subset")
        exit(1)  # pylint: disable=consider-using-sys-exit

    # Process the subset
    for project in projects_subset:
        row = process_gcp_project(project)
        if row:
            data.append(row)
            for k in totals:
                if k != "project_id":
                    totals[k] += row[k]

    data.append(totals)

    # Generate output filenames with subset information
    csv_filename = f"{args.output_prefix}_subset_{args.subset_index}.csv"
    exceptions_filename = f"{args.output_prefix}_subset_{args.subset_index}_exceptions.txt"

    # Output results
    print(f"\nSubset {args.subset_index} Results:")
    print(tabulate(data, headers=headers, tablefmt="grid", maxheadercolwidths=[10, 15, 15, 10, 15, 15, 15, 15, 12]))

    # Save CSV
    with open(csv_filename, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=headers.keys())
        csv_writer.writeheader()
        csv_writer.writerows(data)

    log.info("CSV file saved to: ./%s", csv_filename)

    # Save exceptions if any
    if service_disabled_calls:
        MSG = (
            "Some API service calls were disabled in certain projects, preventing data processing. "
            "These APIs might be intentionally disabled in your environment. "
            f"Details have been captured and saved to: ./{exceptions_filename} for your review."
        )
        log.warning(MSG)

        with open(exceptions_filename, "w", encoding="utf-8") as f:
            f.write(f"Subset {args.subset_index} Exceptions\n")
            f.write("=" * 50 + "\n\n")
            for project_id, messages in service_disabled_calls.items():
                f.write(f"Project ID: {project_id}\n")
                for msg in set(messages):
                    f.write(f"- {msg}\n")
                f.write("\n")


if __name__ == "__main__":
    main()
