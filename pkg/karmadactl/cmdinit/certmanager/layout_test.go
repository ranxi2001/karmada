/*
Copyright 2026 The Karmada Authors.

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

package certmanager

import (
	"slices"
	"testing"

	"github.com/karmada-io/karmada/pkg/karmadactl/options"
	"github.com/karmada-io/karmada/pkg/util/names"
)

func TestNewPlanLegacy(t *testing.T) {
	plan, err := NewPlan(LayoutLegacy, false)
	if err != nil {
		t.Fatalf("NewPlan() error = %v", err)
	}
	if plan.Layout != LayoutLegacy {
		t.Fatalf("layout = %q, want %q", plan.Layout, LayoutLegacy)
	}
	if _, ok := findSecret(plan, options.KarmadaCertsName); !ok {
		t.Fatalf("legacy plan should include %q", options.KarmadaCertsName)
	}
	apiPlan := plan.Components[ComponentAPIServer]
	if got := apiPlan.Paths[PathTLSCertFile]; got != "/etc/karmada/pki/apiserver.crt" {
		t.Fatalf("legacy apiserver tls cert path = %q", got)
	}
	if len(apiPlan.VolumeMounts) != 1 || apiPlan.VolumeMounts[0].MountPath != "/etc/karmada/pki" {
		t.Fatalf("legacy apiserver mounts = %#v", apiPlan.VolumeMounts)
	}
}

func TestNewPlanSplit(t *testing.T) {
	plan, err := NewPlan(LayoutSplit, false)
	if err != nil {
		t.Fatalf("NewPlan() error = %v", err)
	}
	if plan.Layout != LayoutSplit {
		t.Fatalf("layout = %q, want %q", plan.Layout, LayoutSplit)
	}

	tests := []struct {
		secret string
		key    string
		ref    MaterialRef
	}{
		{SecretAPIServerServer, KeyTLSCrt, MaterialRef{ID: APIServerServer, Part: PartCert}},
		{SecretAPIServerEtcdClient, KeyTLSKey, MaterialRef{ID: APIServerEtcdClient, Part: PartKey}},
		{SecretAPIServerServiceAccountKeys, KeySAPub, MaterialRef{ID: APIServerServiceAccountKeyPair, Part: PartPublicKey}},
		{SecretKubeControllerManagerCA, KeyTLSKey, MaterialRef{ID: RootCA, Part: PartKey}},
	}
	for _, tt := range tests {
		secret, ok := findSecret(plan, tt.secret)
		if !ok {
			t.Fatalf("split plan missing secret %q", tt.secret)
		}
		if got := secret.Data[tt.key]; got != tt.ref {
			t.Fatalf("secret %q key %q ref = %#v, want %#v", tt.secret, tt.key, got, tt.ref)
		}
	}

	apiPlan := plan.Components[ComponentAPIServer]
	if got := apiPlan.Paths[PathServiceAccountPublicKeyFile]; got != "/etc/karmada/pki/service-account-key-pair/sa.pub" {
		t.Fatalf("split apiserver sa pub path = %q", got)
	}
	if got := apiPlan.Paths[PathTLSCertFile]; got != "/etc/karmada/pki/server/tls.crt" {
		t.Fatalf("split apiserver tls path = %q", got)
	}
	if !hasVolume(apiPlan, serverCertVolumeName, SecretAPIServerServer) {
		t.Fatalf("split apiserver missing server cert volume")
	}

	kubeconfig, ok := findKubeconfig(plan, names.KarmadaSchedulerComponentName)
	if !ok {
		t.Fatalf("split plan missing scheduler kubeconfig")
	}
	if kubeconfig.ClientRef != SchedulerClient {
		t.Fatalf("scheduler kubeconfig client ref = %q, want %q", kubeconfig.ClientRef, SchedulerClient)
	}
}

func TestNewPlanSplitExternalEtcd(t *testing.T) {
	plan, err := NewPlan(LayoutSplit, true)
	if err != nil {
		t.Fatalf("NewPlan() error = %v", err)
	}
	if _, ok := findIdentity(plan, EtcdServer); ok {
		t.Fatalf("external etcd split plan should not require internal etcd server identity")
	}
	if _, ok := findSecret(plan, SecretEtcdServer); ok {
		t.Fatalf("external etcd split plan should not create internal etcd server secret")
	}
	if _, ok := findSecret(plan, SecretAPIServerEtcdClient); !ok {
		t.Fatalf("external etcd split plan should still create apiserver etcd client secret")
	}
	apiserverEtcdClient, _ := findSecret(plan, SecretAPIServerEtcdClient)
	if got := apiserverEtcdClient.Data[KeyTLSCrt]; got.ID != EtcdClient {
		t.Fatalf("external etcd split apiserver etcd client cert ref = %q, want %q", got.ID, EtcdClient)
	}
	if _, ok := findIdentity(plan, APIServerEtcdClient); ok {
		t.Fatalf("external etcd split plan should not generate apiserver-specific etcd client identity")
	}
	if hasCertificateName(plan, string(EtcdServer)) {
		t.Fatalf("external etcd split plan should not read internal etcd server certificate")
	}
	legacySecret, ok := findSecret(plan, options.KarmadaCertsName)
	if !ok {
		t.Fatalf("external etcd split plan should keep legacy-compatible %q secret", options.KarmadaCertsName)
	}
	if got := legacySecret.Data[fileKey(EtcdCA, PartKey)]; !got.Optional {
		t.Fatalf("external etcd split plan should mark legacy etcd CA key optional")
	}
	if got := legacySecret.Data[fileKey(EtcdServer, PartCert)]; got.ID != EtcdServer || !got.Optional {
		t.Fatalf("external etcd split plan should keep optional legacy etcd server cert ref, got %#v", got)
	}
}

func TestNewPlanUnsupportedLayout(t *testing.T) {
	if _, err := NewPlan("unknown", false); err == nil {
		t.Fatalf("NewPlan() expected error for unsupported layout")
	}
}

func findSecret(plan *Plan, name string) (SecretSpec, bool) {
	for _, secret := range plan.Secrets {
		if secret.Name == name {
			return secret, true
		}
	}
	return SecretSpec{}, false
}

func findKubeconfig(plan *Plan, component string) (KubeconfigSpec, bool) {
	name := component + "-config"
	for _, kubeconfig := range plan.Kubeconfigs {
		if kubeconfig.Name == name {
			return kubeconfig, true
		}
	}
	return KubeconfigSpec{}, false
}

func findIdentity(plan *Plan, id IdentityID) (IdentitySpec, bool) {
	for _, identity := range plan.Identities {
		if identity.ID == id {
			return identity, true
		}
	}
	return IdentitySpec{}, false
}

func hasVolume(plan ComponentPlan, name, secret string) bool {
	for _, volume := range plan.Volumes {
		if volume.Name == name && volume.SecretName == secret {
			return true
		}
	}
	return false
}

func hasCertificateName(plan *Plan, name string) bool {
	return slices.Contains(plan.CertificateNames, name)
}
