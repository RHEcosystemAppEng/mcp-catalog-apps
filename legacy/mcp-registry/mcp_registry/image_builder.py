import time

import yaml
from kubernetes.client.rest import ApiException

from mcp_registry.command_def import CommandDef
from mcp_registry.defaults import NODE_BASE_IMAGE
from mcp_registry.utils import ServerRuntime, get_current_namespace, logger


class ImageBuilder:
    def __init__(self, crd_api, server_definition):
        self.crd_api = crd_api
        self.server_definition = server_definition
        self.server_definition_name = server_definition.get("metadata", {}).get("name")

    def _extract_packages(self, server_def):
        return server_def.get("spec", {}).get("server_detail", {}).get("packages", [])

    def _server_runtime(self, packages) -> ServerRuntime:
        if packages:
            if packages[0].get("registry_name", "") == "npm":
                return ServerRuntime.NODE
            if packages[0].get("registry_name", "").lower() == "unknown":
                package_arguments = packages[0].get("package_arguments", [])
                if package_arguments:
                    if package_arguments[0].get("value", "") == "uvx":
                        return ServerRuntime.UVX
            if packages[0].get("registry_name", "") == "docker":
                return ServerRuntime.DOCKER
        return ServerRuntime.UNKNOWN

    def _recommended_base_image(self, server_runtime: ServerRuntime, packages):
        if server_runtime == ServerRuntime.NODE:
            return NODE_BASE_IMAGE
        logger.info("Return None")
        return None

    def _to_command_def(self, server_runtime: ServerRuntime, packages) -> CommandDef:
        command_def = None
        if server_runtime == ServerRuntime.NODE:
            package_name = packages[0].get("name")
            version = packages[0].get("version", "latest")
            command_def = CommandDef("npx", version)
            command_def.add_args(["-y", f"{package_name}"])

            package_arguments = packages[0].get("package_arguments", [])
            for arg in package_arguments:
                if arg.get("value"):
                    command_def.add_arg(arg.get("value"))
                else:
                    logger.warning(
                        f"Package argument {arg} does not have a 'value' key."
                    )
            environment_variables = packages[0].get("environment_variables", [])
            for env_var in environment_variables:
                if env_var.get("name"):
                    command_def.add_env_var(
                        env_var.get("name"), env_var.get("default", "")
                    )
        return command_def

    def _create_pipelinerun(
        self,
        server_runtime: ServerRuntime,
        base_image: str,
        registry: str,
        image_name: str,
        command_def: CommandDef,
    ) -> str:
        # TODO Move to defaults or make configurable
        pr_name = f"{self.server_definition_name}-"
        service_account = "pipeline"
        pipeline_name = "mcp-server-build-pipeline"

        pr_manifest = {
            "apiVersion": "tekton.dev/v1beta1",
            "kind": "PipelineRun",
            "metadata": {"generateName": pr_name},
            "spec": {
                "serviceAccountName": service_account,
                "pipelineRef": {"name": pipeline_name},
                "params": [
                    {"name": "base-image", "value": base_image},
                    {"name": "command", "value": command_def.command},
                    {"name": "args", "value": command_def.to_manifest_args()},
                    {"name": "envs", "value": command_def.to_manifest_env_vars()},
                    {"name": "registry", "value": registry},
                    {"name": "image-name", "value": image_name},
                ],
                "workspaces": [
                    {
                        "name": "shared-workspace",
                        "volumeClaimTemplate": {
                            "spec": {
                                "accessModes": ["ReadWriteOnce"],
                                "resources": {"requests": {"storage": "100Mi"}},
                            }
                        },
                    }
                ],
            },
        }

        group = "tekton.dev"
        version = "v1beta1"
        plural = "pipelineruns"
        namespace = get_current_namespace()
        try:
            pipeline_run = self.crd_api.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                body=pr_manifest,
            )
            print(
                f"PipelineRun '{pr_name}' created with name: {pipeline_run['metadata']['name']}"
            )
            return pipeline_run["metadata"]["name"]
        except ApiException as e:
            manifest = yaml.dump(pr_manifest, indent=2, sort_keys=False)
            logger.warning(f"Failed to deploy:\n{manifest}")
            if e.status == 409:
                print(f"PipelineRun '{pr_name}' already exists, skipping")
            else:
                print("Error creating PipelineRun:", e)
                return

    def wait_for_pipelinerun_completion(
        self, name, timeout_seconds=10 * 60, poll_interval=10
    ):
        group = "tekton.dev"
        version = "v1beta1"
        plural = "pipelineruns"

        start_time = time.time()
        while True:
            try:
                pr = self.crd_api.get_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=get_current_namespace(),
                    plural=plural,
                    name=name,
                )
                conditions = pr.get("status", {}).get("conditions", [])
                for condition in conditions:
                    if condition.get("type") == "Succeeded":
                        status = condition.get("status")
                        if status in ("True", "False"):
                            return status
                logger.info(f"PipelineRun '{name}' is still running...")
            except ApiException as e:
                print(f"Exception when retrieving PipelineRun: {e}")
                raise

            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(
                    f"PipelineRun '{name}' did not complete within {timeout_seconds} seconds."
                )

            time.sleep(poll_interval)

    def build_server_image(self) -> tuple[CommandDef, str]:
        packages = self._extract_packages(self.server_definition)
        if packages:
            server_runtime = self._server_runtime(packages)
            logger.info(
                f"Identified server runtime for {self.server_definition_name} as {server_runtime.value}"
            )
            base_image = self._recommended_base_image(server_runtime, packages)
            if base_image:
                logger.info(
                    f"Building server image for {self.server_definition_name} using base image {base_image}"
                )
                command_def = self._to_command_def(server_runtime, packages)
                if command_def:
                    logger.info(
                        f"Server command and args for {self.server_definition_name}: {command_def}"
                    )
                    registry = f"image-registry.openshift-image-registry.svc:5000/{get_current_namespace()}"
                    image_name = f"{self.server_definition_name}:{command_def.version}"
                    pr_name = self._create_pipelinerun(
                        server_runtime=server_runtime,
                        base_image=base_image,
                        registry=registry,
                        image_name=image_name,
                        command_def=command_def,
                    )
                    logger.info(
                        f"PipelineRun {pr_name} created for {self.server_definition_name} with command: {command_def.command} and args: {command_def.to_manifest_args()}"
                    )

                    status = self.wait_for_pipelinerun_completion(
                        pr_name, timeout_seconds=10 * 60, poll_interval=10
                    )
                    if status == "True":
                        logger.info(
                            f"PipelineRun {pr_name} completed successfully for {self.server_definition_name}."
                        )
                        return command_def, f"{registry}/{image_name}"

                    else:
                        logger.error(
                            f"PipelineRun {pr_name} failed for {self.server_definition_name}."
                        )
                    return None
                else:
                    logger.warning(
                        f"No server command and args found for {self.server_definition_name}."
                    )
            else:
                pkgs = yaml.dump(packages, indent=2, sort_keys=False)
                logger.warning(
                    f"No recommended base image found for {self.server_definition_name}:\n {pkgs}"
                )
        else:
            logger.warning(
                f"No packages found in {self.server_definition_name}. Cannot build image."
            )
        return None
