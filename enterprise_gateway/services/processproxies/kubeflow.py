# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
"""Code related to managing kernels running in Kubernetes clusters."""

import logging
import os
import urllib3

from kubernetes import client, config

from .k8s import KubernetesProcessProxy

urllib3.disable_warnings()

# Default logging level of kubernetes produces too much noise - raise to warning only.
logging.getLogger('kubernetes').setLevel(os.environ.get('EG_KUBERNETES_LOG_LEVEL', logging.WARNING))

enterprise_gateway_namespace = os.environ.get('EG_NAMESPACE', 'default')
default_kernel_service_account_name = os.environ.get('EG_DEFAULT_KERNEL_SERVICE_ACCOUNT_NAME', 'default')
kernel_cluster_role = os.environ.get('EG_KERNEL_CLUSTER_ROLE', 'cluster-admin')
share_gateway_namespace = bool(os.environ.get('EG_SHARED_NAMESPACE', 'False').lower() == 'true')

config.load_incluster_config()


class KubeflowProcessProxy(KubernetesProcessProxy):
    """
    Kernel lifecycle management for Kubernetes kernels.
    """
    def __init__(self, kernel_manager, proxy_config):
        super(KubeflowProcessProxy, self).__init__(kernel_manager, proxy_config)

        self.kernel_name = None
        self.kernel_pod_name = None
        self.kernel_namespace = None
        self.delete_kernel_namespace = False

    def get_container_status(self, iteration):
        """Return current container state."""
        # Locates the kernel pod using the kernel_id selector.  If the phase indicates Running, the pod's IP
        # is used for the assigned_ip.
        pod_status = None
        ret = client.CoreV1Api().list_namespaced_pod(namespace=self.kernel_namespace,
                                                     label_selector="kernel_id=" + self.kernel_id)
        if ret and ret.items:
            pod_info = ret.items[0]
            self.container_name = pod_info.metadata.name
            self.kernel_name = pod_info.metadata.labels["kernel"]
            if pod_info.status:
                pod_status = pod_info.status.phase
                if pod_status == 'Running' and self.assigned_host == '':
                    # Pod is running, capture IP
                    self.assigned_ip = pod_info.status.pod_ip
                    self.assigned_host = self.container_name
                    self.assigned_node_ip = pod_info.status.host_ip

        if iteration:  # only log if iteration is not None (otherwise poll() is too noisy)
            self.log.debug("{}: Waiting to connect to k8s pod in namespace '{}'. "
                           "Name: '{}', Status: '{}', Pod IP: '{}', KernelID: '{}'".
                           format(iteration, self.kernel_namespace, self.container_name, pod_status,
                                  self.assigned_ip, self.kernel_id))

        return pod_status

    def terminate_container_resources(self):
        """Terminate any artifacts created on behalf of the container's lifetime."""
        # Kubernetes objects don't go away on their own - so we need to tear down the namespace
        # or pod associated with the kernel.  If we created the namespace and we're not in the
        # the process of restarting the kernel, then that's our target, else just delete the pod.

        result = False
        body = client.V1DeleteOptions(grace_period_seconds=0, propagation_policy='Background')

        if self.delete_kernel_namespace and not self.kernel_manager.restarting:
            object_name = 'namespace'
        else:
            object_name = 'jupyterkernel'

        # Delete the namespace or pod...
        try:
            # What gets returned from this call is a 'V1Status'.  It looks a bit like JSON but appears to be
            # intentionally obfuscated.  Attempts to load the status field fail due to malformed json.  As a
            # result, we'll see if the status field contains either 'Succeeded' or 'Failed' - since that should
            # indicate the phase value.

            if self.delete_kernel_namespace and not self.kernel_manager.restarting:
                v1_status = client.CoreV1Api().delete_namespace(name=self.kernel_namespace, body=body)
                if v1_status and v1_status.status:
                    termination_stati = ['Succeeded', 'Failed', 'Terminating']
                    if any(status in v1_status.status for status in termination_stati):
                        result = True
            else:
                # TODO(gaocegege): Check the response
                api_response = client.CustomObjectsApi().delete_namespaced_custom_object(
                    group='kubeflow.tkestack.io',
                    version='v1alpha1',
                    plural='jupyterkernels',
                    namespace=self.kernel_namespace, body=body,
                    name=self.kernel_name)
                if api_response:
                    result = True

            if not result:
                self.log.warning("Unable to delete {}: {}".format(object_name, v1_status))
        except Exception as err:
            if isinstance(err, client.rest.ApiException) and err.status == 404:
                result = True  # okay if its not found
            else:
                self.log.warning("Error occurred deleting {}: {}".format(object_name, err))

        if result:
            self.log.debug("KubeflowProcessProxy.terminate_container_resources, kernel: {}.{}, kernel ID: {} has "
                           "been terminated.".format(self.kernel_namespace, self.kernel_name, self.kernel_id))
            self.container_name = None
            self.kernel_name = None
            result = None  # maintain jupyter contract
        else:
            self.log.warning("KubeflowProcessProxy.terminate_container_resources, kernel: {}.{}, kernel ID: {} has "
                             "not been terminated.".format(self.kernel_namespace, self.kernel_name, self.kernel_id))
        return result
