/*
Copyright 2025 The Karmada Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package kubernetes

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/certmanager"
	initConfig "github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/config"
	"github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/options"
	"github.com/karmada-io/karmada/pkg/karmadactl/util"
)

func (i *CommandInitOption) defaultEtcdContainerCommand() []string {
	paths := i.componentPaths(certmanager.ComponentEtcd)
	var etcdClusterConfig strings.Builder
	for v := int32(0); v < i.EtcdReplicas; v++ {
		etcdClusterConfig.WriteString(fmt.Sprintf("%s-%v=http://%s-%v.%s.%s.svc.%s:%v", etcdStatefulSetAndServiceName, v, etcdStatefulSetAndServiceName, v, etcdStatefulSetAndServiceName, i.Namespace, i.HostClusterDomain, etcdContainerServerPort) + ",")
	}

	command := []string{
		"/usr/local/bin/etcd",
		fmt.Sprintf("--name=$(%s)", etcdEnvPodName),
		fmt.Sprintf("--listen-peer-urls=http://$(%s):%v", etcdEnvPodIP, etcdContainerServerPort),
		fmt.Sprintf("--listen-client-urls=https://$(%s):%v,http://127.0.0.1:%v", etcdEnvPodIP, etcdContainerClientPort, etcdContainerClientPort),
		fmt.Sprintf("--listen-metrics-urls=http://$(%s):%v", etcdEnvPodIP, etcdContainerMetricsPort),
		fmt.Sprintf("--advertise-client-urls=https://$(%s).%s.%s.svc.%s:%v", etcdEnvPodName, etcdStatefulSetAndServiceName, i.Namespace, i.HostClusterDomain, etcdContainerClientPort),
		fmt.Sprintf("--initial-cluster=%s", strings.TrimRight(etcdClusterConfig.String(), ",")),
		"--initial-cluster-state=new",
		"--client-cert-auth=true",
		fmt.Sprintf("--cert-file=%s", paths[certmanager.PathTLSCertFile]),
		fmt.Sprintf("--key-file=%s", paths[certmanager.PathTLSKeyFile]),
		fmt.Sprintf("--trusted-ca-file=%s", paths[certmanager.PathClientCAFile]),
		fmt.Sprintf("--data-dir=%s", etcdContainerDataVolumeMountPath),
		fmt.Sprintf("--cipher-suites=%s", etcdCipherSuites),
		"--initial-cluster-token=etcd-cluster",
		fmt.Sprintf("--initial-advertise-peer-urls=http://$(%s):%v", etcdEnvPodIP, etcdContainerServerPort),
		"--peer-client-cert-auth=false",
		fmt.Sprintf("--peer-trusted-ca-file=%s", paths[certmanager.PathEtcdPeerCAFile]),
		fmt.Sprintf("--peer-key-file=%s", paths[certmanager.PathEtcdPeerKeyFile]),
		fmt.Sprintf("--peer-cert-file=%s", paths[certmanager.PathEtcdPeerCertFile]),
	}
	return command
}

func (i *CommandInitOption) defaultKarmadaAPIServerContainerCommand() []string {
	paths := i.componentPaths(certmanager.ComponentAPIServer)
	var etcdServers string
	if etcdServers = i.ExternalEtcdServers; etcdServers == "" {
		etcdServers = strings.TrimRight(i.etcdServers(), ",")
	}
	command := []string{
		"kube-apiserver",
		"--allow-privileged=true",
		"--authorization-mode=Node,RBAC",
		fmt.Sprintf("--client-ca-file=%s", paths[certmanager.PathClientCAFile]),
		"--enable-bootstrap-token-auth=true",
		fmt.Sprintf("--etcd-cafile=%s", paths[certmanager.PathEtcdCAFile]),
		fmt.Sprintf("--etcd-certfile=%s", paths[certmanager.PathEtcdCertFile]),
		fmt.Sprintf("--etcd-keyfile=%s", paths[certmanager.PathEtcdKeyFile]),
		fmt.Sprintf("--etcd-servers=%s", etcdServers),
		"--bind-address=0.0.0.0",
		"--disable-admission-plugins=StorageObjectInUseProtection,ServiceAccount",
		"--runtime-config=",
		fmt.Sprintf("--apiserver-count=%v", i.KarmadaAPIServerReplicas),
		fmt.Sprintf("--secure-port=%v", karmadaAPIServerContainerPort),
		fmt.Sprintf("--service-account-issuer=https://kubernetes.default.svc.%s", i.HostClusterDomain),
		fmt.Sprintf("--service-account-key-file=%s", paths[certmanager.PathServiceAccountPublicKeyFile]),
		fmt.Sprintf("--service-account-signing-key-file=%s", paths[certmanager.PathServiceAccountPrivateKeyFile]),
		fmt.Sprintf("--service-cluster-ip-range=%s", serviceClusterIP),
		fmt.Sprintf("--proxy-client-cert-file=%s", paths[certmanager.PathProxyClientCertFile]),
		fmt.Sprintf("--proxy-client-key-file=%s", paths[certmanager.PathProxyClientKeyFile]),
		"--requestheader-allowed-names=front-proxy-client",
		fmt.Sprintf("--requestheader-client-ca-file=%s", paths[certmanager.PathRequestHeaderClientCAFile]),
		"--requestheader-extra-headers-prefix=X-Remote-Extra-",
		"--requestheader-group-headers=X-Remote-Group",
		"--requestheader-username-headers=X-Remote-User",
		fmt.Sprintf("--tls-cert-file=%s", paths[certmanager.PathTLSCertFile]),
		fmt.Sprintf("--tls-private-key-file=%s", paths[certmanager.PathTLSKeyFile]),
		"--tls-min-version=VersionTLS13",
		"--v=2",
	}
	if i.ExternalEtcdKeyPrefix != "" {
		command = append(command, fmt.Sprintf("--etcd-prefix=%s", i.ExternalEtcdKeyPrefix))
	}
	return command
}

func (i *CommandInitOption) defaultKarmadaSchedulerContainerCommand() []string {
	paths := i.componentPaths(certmanager.ComponentScheduler)
	return []string{
		"/bin/karmada-scheduler",
		fmt.Sprintf("--kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		"--metrics-bind-address=$(POD_IP):8080",
		"--health-probe-bind-address=$(POD_IP):10351",
		"--enable-scheduler-estimator=true",
		"--leader-elect=true",
		fmt.Sprintf("--scheduler-estimator-ca-file=%s", paths[certmanager.PathSchedulerEstimatorCAFile]),
		fmt.Sprintf("--scheduler-estimator-cert-file=%s", paths[certmanager.PathSchedulerEstimatorCertFile]),
		fmt.Sprintf("--scheduler-estimator-key-file=%s", paths[certmanager.PathSchedulerEstimatorKeyFile]),
		fmt.Sprintf("--leader-elect-resource-namespace=%s", i.Namespace),
		"--v=2",
	}
}

// default command line arguments for kube-controller-manager
func (i *CommandInitOption) defaultKarmadaKubeControllerManagerContainerCommand() []string {
	paths := i.componentPaths(certmanager.ComponentKubeControllerManager)
	return []string{
		"kube-controller-manager",
		"--allocate-node-cidrs=true",
		fmt.Sprintf("--kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		fmt.Sprintf("--authentication-kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		fmt.Sprintf("--authorization-kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		"--bind-address=0.0.0.0",
		fmt.Sprintf("--client-ca-file=%s", paths[certmanager.PathClientCAFile]),
		"--cluster-cidr=10.244.0.0/16",
		fmt.Sprintf("--cluster-name=%s", options.ClusterName),
		fmt.Sprintf("--cluster-signing-cert-file=%s", paths[certmanager.PathClusterSigningCertFile]),
		fmt.Sprintf("--cluster-signing-key-file=%s", paths[certmanager.PathClusterSigningKeyFile]),
		"--controllers=namespace,garbagecollector,serviceaccount-token,ttl-after-finished,bootstrapsigner,tokencleaner,csrcleaner,csrsigning,clusterrole-aggregation",
		"--leader-elect=true",
		fmt.Sprintf("--leader-elect-resource-namespace=%s", i.Namespace),
		"--node-cidr-mask-size=24",
		fmt.Sprintf("--root-ca-file=%s", paths[certmanager.PathRootCAFile]),
		fmt.Sprintf("--service-account-private-key-file=%s", paths[certmanager.PathServiceAccountPrivateKeyFile]),
		fmt.Sprintf("--service-cluster-ip-range=%s", serviceClusterIP),
		"--use-service-account-credentials=true",
		"--v=2",
	}
}

func (i *CommandInitOption) defaultKarmadaControllerManagerContainerCommand() []string {
	return []string{
		"/bin/karmada-controller-manager",
		fmt.Sprintf("--kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		"--metrics-bind-address=$(POD_IP):8080",
		"--health-probe-bind-address=$(POD_IP):10357",
		"--cluster-status-update-frequency=10s",
		fmt.Sprintf("--leader-elect-resource-namespace=%s", i.Namespace),
		"--v=2",
	}
}

func (i *CommandInitOption) defaultKarmadaWebhookContainerCommand() []string {
	paths := i.componentPaths(certmanager.ComponentWebhook)
	return []string{
		"/bin/karmada-webhook",
		fmt.Sprintf("--kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		"--bind-address=$(POD_IP)",
		"--metrics-bind-address=$(POD_IP):8080",
		"--health-probe-bind-address=$(POD_IP):8000",
		fmt.Sprintf("--secure-port=%v", webhookTargetPort),
		fmt.Sprintf("--cert-dir=%s", paths[certmanager.PathWebhookCertDir]),
		"--v=2",
	}
}

func (i *CommandInitOption) defaultKarmadaAggregatedAPIServerContainerCommand() []string {
	paths := i.componentPaths(certmanager.ComponentAggregatedAPIServer)
	var etcdServers string
	if etcdServers = i.ExternalEtcdServers; etcdServers == "" {
		etcdServers = strings.TrimRight(i.etcdServers(), ",")
	}
	command := []string{
		"/bin/karmada-aggregated-apiserver",
		fmt.Sprintf("--kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		fmt.Sprintf("--authentication-kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		fmt.Sprintf("--authorization-kubeconfig=%s", filepath.Join(karmadaConfigVolumeMountPath, util.KarmadaConfigFieldName)),
		fmt.Sprintf("--etcd-servers=%s", etcdServers),
		fmt.Sprintf("--etcd-cafile=%s", paths[certmanager.PathEtcdCAFile]),
		fmt.Sprintf("--etcd-certfile=%s", paths[certmanager.PathEtcdCertFile]),
		fmt.Sprintf("--etcd-keyfile=%s", paths[certmanager.PathEtcdKeyFile]),
		fmt.Sprintf("--tls-cert-file=%s", paths[certmanager.PathTLSCertFile]),
		fmt.Sprintf("--tls-private-key-file=%s", paths[certmanager.PathTLSKeyFile]),
		"--tls-min-version=VersionTLS13",
		"--audit-log-path=-",
		"--audit-log-maxage=0",
		"--audit-log-maxbackup=0",
		"--bind-address=$(POD_IP)",
		"--v=2",
	}
	if i.ExternalEtcdKeyPrefix != "" {
		command = append(command, fmt.Sprintf("--etcd-prefix=%s", i.ExternalEtcdKeyPrefix))
	}
	return command
}

func setComponentArgs(cliExtraArgs []string, cfgArgs []initConfig.Arg) ([]string, error) {
	// validate
	if err := validateCfgExtraArgs(cfgArgs); err != nil {
		return nil, err
	}
	// Check if there are command line arguments and whether merging is needed.
	mergedArgs := cfgArgs
	if cliExtraArgs != nil {
		cliArgs := parseExtraArgs(cliExtraArgs)
		mergedArgs = mergeArgs(cfgArgs, cliArgs)
	}
	return convertArgsToCmdLineFlags(mergedArgs), nil
}

// validateCfgExtraArgs validate cfg extra arguments.
func validateCfgExtraArgs(args []initConfig.Arg) error {
	for id, arg := range args {
		if len(arg.Name) == 0 {
			return fmt.Errorf("the extra args[%d] name is empty", id)
		}
	}
	return nil
}

func parseExtraArgs(extraArgs []string) []initConfig.Arg {
	if len(extraArgs) == 0 {
		return nil
	}

	var result []initConfig.Arg
	for _, arg := range extraArgs {
		arg = strings.TrimPrefix(arg, "--")
		part := strings.SplitN(arg, "=", 2)
		if len(part) == 2 {
			result = append(result, initConfig.Arg{
				Name:  part[0],
				Value: part[1],
			})
		} else {
			result = append(result, initConfig.Arg{
				Name:  part[0],
				Value: "",
			})
		}
	}
	return result
}

func mergeArgs(cfgArgs []initConfig.Arg, cliArgs []initConfig.Arg) []initConfig.Arg {
	merged := map[string]initConfig.Arg{}

	// Cli parameters
	for _, arg := range cliArgs {
		merged[arg.Name] = arg
	}

	// Cover
	for _, arg := range cfgArgs {
		merged[arg.Name] = arg
	}

	result := make([]initConfig.Arg, 0, len(merged))

	for _, arg := range merged {
		result = append(result, arg)
	}

	return result
}

// convertArgsToCmdLineFlags formats the arguments into --key=value.
func convertArgsToCmdLineFlags(args []initConfig.Arg) []string {
	if len(args) == 0 {
		return nil
	}

	res := make([]string, 0, len(args))
	for _, arg := range args {
		if arg.Value != "" {
			res = append(res, fmt.Sprintf("--%s=%s", arg.Name, arg.Value))
		} else {
			res = append(res, fmt.Sprintf("--%s", arg.Name))
		}
	}
	return res
}
