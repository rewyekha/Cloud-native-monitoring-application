from kubernetes import client, config
import yaml
import os

def load_kube_config():
    """Load Kubernetes configuration"""
    try:
        config.load_incluster_config()  # For running inside cluster
    except:
        config.load_kube_config()  # For running locally

def create_namespace(api_instance, namespace_name):
    """Create namespace if it doesn't exist"""
    try:
        api_instance.read_namespace(name=namespace_name)
        print(f"Namespace '{namespace_name}' already exists")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            namespace = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace_name)
            )
            api_instance.create_namespace(body=namespace)
            print(f"Created namespace '{namespace_name}'")

def create_configmap(api_instance, namespace):
    """Create ConfigMap for application configuration"""
    config_data = {
        "FLASK_ENV": "production",
        "REFRESH_INTERVAL": "30"
    }
    
    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name="monitoring-app-config"),
        data=config_data
    )
    
    try:
        api_instance.create_namespaced_config_map(
            namespace=namespace,
            body=configmap
        )
        print("ConfigMap created successfully")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print("ConfigMap already exists")
        else:
            raise e

def create_deployment(api_instance, namespace, image_uri):
    """Create enhanced deployment with best practices"""
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name="monitoring-app",
            labels={"app": "monitoring-app", "version": "v1"}
        ),
        spec=client.V1DeploymentSpec(
            replicas=2,  # Multiple replicas for high availability
            selector=client.V1LabelSelector(
                match_labels={"app": "monitoring-app"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": "monitoring-app", "version": "v1"}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="monitoring-app",
                            image=image_uri,
                            ports=[
                                client.V1ContainerPort(container_port=5000, name="http")
                            ],
                            env=[
                                client.V1EnvVar(
                                    name="FLASK_ENV",
                                    value_from=client.V1EnvVarSource(
                                        config_map_key_ref=client.V1ConfigMapKeySelector(
                                            name="monitoring-app-config",
                                            key="FLASK_ENV"
                                        )
                                    )
                                )
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "128Mi", "cpu": "100m"},
                                limits={"memory": "512Mi", "cpu": "500m"}
                            ),
                            liveness_probe=client.V1Probe(
                                http_get=client.V1HTTPGetAction(
                                    path="/health",
                                    port=5000
                                ),
                                initial_delay_seconds=30,
                                period_seconds=10
                            ),
                            readiness_probe=client.V1Probe(
                                http_get=client.V1HTTPGetAction(
                                    path="/health",
                                    port=5000
                                ),
                                initial_delay_seconds=5,
                                period_seconds=5
                            ),
                            security_context=client.V1SecurityContext(
                                run_as_non_root=True,
                                run_as_user=1000,
                                read_only_root_filesystem=True
                            )
                        )
                    ],
                    security_context=client.V1PodSecurityContext(
                        fs_group=1000
                    )
                )
            )
        )
    )
    
    try:
        api_instance.create_namespaced_deployment(
            namespace=namespace,
            body=deployment
        )
        print("Deployment created successfully")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print("Deployment already exists")
        else:
            raise e

def create_service(api_instance, namespace):
    """Create service with LoadBalancer type"""
    service = client.V1Service(
        metadata=client.V1ObjectMeta(
            name="monitoring-app-service",
            labels={"app": "monitoring-app"}
        ),
        spec=client.V1ServiceSpec(
            type="LoadBalancer",
            selector={"app": "monitoring-app"},
            ports=[
                client.V1ServicePort(
                    port=80,
                    target_port=5000,
                    protocol="TCP",
                    name="http"
                )
            ]
        )
    )
    
    try:
        api_instance.create_namespaced_service(
            namespace=namespace,
            body=service
        )
        print("Service created successfully")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print("Service already exists")
        else:
            raise e

def create_hpa(api_instance, namespace):
    """Create Horizontal Pod Autoscaler"""
    hpa = client.V2HorizontalPodAutoscaler(
        metadata=client.V1ObjectMeta(name="monitoring-app-hpa"),
        spec=client.V2HorizontalPodAutoscalerSpec(
            scale_target_ref=client.V2CrossVersionObjectReference(
                api_version="apps/v1",
                kind="Deployment",
                name="monitoring-app"
            ),
            min_replicas=1,
            max_replicas=5,
            metrics=[
                client.V2MetricSpec(
                    type="Resource",
                    resource=client.V2ResourceMetricSource(
                        name="cpu",
                        target=client.V2MetricTarget(
                            type="Utilization",
                            average_utilization=70
                        )
                    )
                )
            ]
        )
    )
    
    try:
        autoscaling_api = client.AutoscalingV2Api()
        autoscaling_api.create_namespaced_horizontal_pod_autoscaler(
            namespace=namespace,
            body=hpa
        )
        print("HPA created successfully")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print("HPA already exists")
        else:
            raise e

def main():
    """Main deployment function"""
    # Load Kubernetes configuration
    load_kube_config()
    
    # Configuration
    namespace = "monitoring"
    image_uri = os.getenv("IMAGE_URI", "568373317874.dkr.ecr.us-east-1.amazonaws.com/my_monitoring_app_image:latest")
    
    # Create API clients
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    
    print("Starting Kubernetes deployment...")
    
    # Create resources
    create_namespace(core_v1, namespace)
    create_configmap(core_v1, namespace)
    create_deployment(apps_v1, namespace, image_uri)
    create_service(core_v1, namespace)
    create_hpa(None, namespace)
    
    print("Deployment completed successfully!")
    print(f"Monitor your deployment with:")
    print(f"kubectl get pods -n {namespace}")
    print(f"kubectl get services -n {namespace}")
    print(f"kubectl logs -f deployment/monitoring-app -n {namespace}")

if __name__ == "__main__":
    main()