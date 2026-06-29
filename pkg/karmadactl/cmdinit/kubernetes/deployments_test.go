/*
Copyright 2023 The Karmada Authors.

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
	"slices"
	"testing"

	corev1 "k8s.io/api/core/v1"

	"github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/certmanager"
)

func TestCommandInitOption_etcdServers(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	if got := cmdOpt.etcdServers(); got == "" {
		t.Errorf("CommandInitOption.etcdServers() = %v, want none empty", got)
	}
}

func TestCommandInitOption_karmadaAPIServerContainerCommand(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	flags := cmdOpt.defaultKarmadaAPIServerContainerCommand()
	if len(flags) == 0 {
		t.Errorf("CommandInitOption.defaultKarmadaAPIServerContainerCommand() returns empty")
	}
}

func TestCommandInitOption_makeKarmadaAPIServerDeployment(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	deployment := cmdOpt.makeKarmadaAPIServerDeployment()
	if deployment == nil {
		t.Error("CommandInitOption.makeKarmadaAPIServerDeployment() returns nil")
	}
}

func TestCommandInitOption_makeKarmadaKubeControllerManagerDeployment(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	deployment := cmdOpt.makeKarmadaKubeControllerManagerDeployment()
	if deployment == nil {
		t.Error("CommandInitOption.makeKarmadaKubeControllerManagerDeployment() returns nil")
	}
}

func TestCommandInitOption_makeKarmadaSchedulerDeployment(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	deployment := cmdOpt.makeKarmadaSchedulerDeployment()
	if deployment == nil {
		t.Error("CommandInitOption.makeKarmadaSchedulerDeployment() returns nil")
	}
}

func TestCommandInitOption_makeKarmadaControllerManagerDeployment(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	deployment := cmdOpt.makeKarmadaControllerManagerDeployment()
	if deployment == nil {
		t.Error("CommandInitOption.makeKarmadaControllerManagerDeployment() returns nil")
	}
}

func TestCommandInitOption_makeKarmadaWebhookDeployment(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	deployment := cmdOpt.makeKarmadaWebhookDeployment()
	if deployment == nil {
		t.Error("CommandInitOption.makeKarmadaWebhookDeployment() returns nil")
	}
}

func TestCommandInitOption_makeKarmadaAggregatedAPIServerDeployment(t *testing.T) {
	cmdOpt := CommandInitOption{EtcdReplicas: 1, Namespace: "karmada"}
	deployment := cmdOpt.makeKarmadaAggregatedAPIServerDeployment()
	if deployment == nil {
		t.Error("CommandInitOption.makeKarmadaAggregatedAPIServerDeployment() returns nil")
	}
}

func TestCommandInitOption_splitSecretLayout(t *testing.T) {
	cmdOpt := CommandInitOption{
		EtcdReplicas:       1,
		Namespace:          "karmada-system",
		HostClusterDomain:  "cluster.local",
		SecretLayout:       certmanager.LayoutSplit,
		KarmadaAPIServerIP: nil,
	}

	command := cmdOpt.defaultKarmadaAPIServerContainerCommand()
	if !slices.Contains(command, "--tls-cert-file=/etc/karmada/pki/server/tls.crt") {
		t.Fatalf("split apiserver command missing split tls cert path: %v", command)
	}
	if !slices.Contains(command, "--service-account-key-file=/etc/karmada/pki/service-account-key-pair/sa.pub") {
		t.Fatalf("split apiserver command missing service account public key path: %v", command)
	}

	deployment := cmdOpt.makeKarmadaAPIServerDeployment()
	if deployment == nil {
		t.Fatal("CommandInitOption.makeKarmadaAPIServerDeployment() returns nil")
	}
	volumes := deployment.Spec.Template.Spec.Volumes
	if !hasSecretVolume(volumes, "server-cert", certmanager.SecretAPIServerServer) {
		t.Fatalf("split apiserver deployment missing server-cert volume: %#v", volumes)
	}
	if !hasSecretVolume(volumes, "service-account-key-pair", certmanager.SecretAPIServerServiceAccountKeys) {
		t.Fatalf("split apiserver deployment missing service-account-key-pair volume: %#v", volumes)
	}
}

func hasSecretVolume(volumes []corev1.Volume, name, secretName string) bool {
	for _, volume := range volumes {
		if volume.Name == name && volume.Secret != nil && volume.Secret.SecretName == secretName {
			return true
		}
	}
	return false
}
