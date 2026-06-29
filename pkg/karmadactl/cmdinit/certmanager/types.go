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
	corev1 "k8s.io/api/core/v1"
	certutil "k8s.io/client-go/util/cert"
)

const (
	// LayoutLegacy keeps the current aggregated certificate Secret layout.
	LayoutLegacy = "legacy"
	// LayoutSplit stores generated certificate materials in component-scoped Secrets.
	LayoutSplit = "split"
)

// IdentityID identifies one certificate or key-pair material in a certificate plan.
type IdentityID string

// SignerID identifies the CA material used to sign a certificate identity.
type SignerID string

// MaterialPart identifies which part of an identity should be written to a Secret key.
type MaterialPart string

// PathRole identifies a component command-line flag path provided by a component plan.
type PathRole string

// IdentityKind classifies the material represented by an identity.
type IdentityKind string

const (
	// KindCertificate identifies certificate and private key material.
	KindCertificate IdentityKind = "certificate"
	// KindKeyPair identifies private and public key-pair material.
	KindKeyPair IdentityKind = "keyPair"
)

const (
	// PartCert identifies certificate data.
	PartCert MaterialPart = "cert"
	// PartKey identifies private key data.
	PartKey MaterialPart = "key"
	// PartPublicKey identifies public key data.
	PartPublicKey MaterialPart = "publicKey"
)

// Certificate identity constants name generated certificate and key-pair materials.
const (
	RootCA                         IdentityID = "ca"
	EtcdCA                         IdentityID = "etcd-ca"
	EtcdServer                     IdentityID = "etcd-server"
	EtcdClient                     IdentityID = "etcd-client"
	AdminClient                    IdentityID = "karmada"
	APIServerServer                IdentityID = "apiserver"
	FrontProxyCA                   IdentityID = "front-proxy-ca"
	FrontProxyClient               IdentityID = "front-proxy-client"
	AggregatedAPIServerServer      IdentityID = "karmada-aggregated-apiserver"
	WebhookServer                  IdentityID = "karmada-webhook"
	APIServerEtcdClient            IdentityID = "karmada-apiserver-etcd-client"
	AggregatedAPIServerEtcdClient  IdentityID = "karmada-aggregated-apiserver-etcd-client"
	ControllerManagerClient        IdentityID = "karmada-controller-manager-client"
	SchedulerClient                IdentityID = "karmada-scheduler-client"
	AggregatedAPIServerClient      IdentityID = "karmada-aggregated-apiserver-client"
	WebhookClient                  IdentityID = "karmada-webhook-client"
	KubeControllerManagerClient    IdentityID = "kube-controller-manager-client"
	DeschedulerClient              IdentityID = "karmada-descheduler-client"
	SearchClient                   IdentityID = "karmada-search-client"
	MetricsAdapterClient           IdentityID = "karmada-metrics-adapter-client"
	SchedulerEstimatorClient       IdentityID = "karmada-scheduler-grpc"
	DeschedulerEstimatorClient     IdentityID = "karmada-descheduler-grpc"
	APIServerServiceAccountKeyPair IdentityID = "karmada-apiserver-service-account-key-pair"
)

// Path role constants describe certificate-related component command paths.
const (
	PathClientCAFile                 PathRole = "client-ca-file"
	PathEtcdCAFile                   PathRole = "etcd-ca-file"
	PathEtcdCertFile                 PathRole = "etcd-cert-file"
	PathEtcdKeyFile                  PathRole = "etcd-key-file"
	PathServiceAccountPublicKeyFile  PathRole = "service-account-public-key-file"
	PathServiceAccountPrivateKeyFile PathRole = "service-account-private-key-file"
	PathProxyClientCertFile          PathRole = "proxy-client-cert-file"
	PathProxyClientKeyFile           PathRole = "proxy-client-key-file"
	PathRequestHeaderClientCAFile    PathRole = "requestheader-client-ca-file"
	PathTLSCertFile                  PathRole = "tls-cert-file"
	PathTLSKeyFile                   PathRole = "tls-key-file"
	PathClusterSigningCertFile       PathRole = "cluster-signing-cert-file"
	PathClusterSigningKeyFile        PathRole = "cluster-signing-key-file"
	PathRootCAFile                   PathRole = "root-ca-file"
	PathSchedulerEstimatorCAFile     PathRole = "scheduler-estimator-ca-file"
	PathSchedulerEstimatorCertFile   PathRole = "scheduler-estimator-cert-file"
	PathSchedulerEstimatorKeyFile    PathRole = "scheduler-estimator-key-file"
	PathWebhookCertDir               PathRole = "webhook-cert-dir"
	PathEtcdPeerCAFile               PathRole = "etcd-peer-ca-file"
	PathEtcdPeerCertFile             PathRole = "etcd-peer-cert-file"
	PathEtcdPeerKeyFile              PathRole = "etcd-peer-key-file"
)

const (
	// KeyCACrt is the Secret data key for a CA certificate.
	KeyCACrt = "ca.crt"
	// KeyTLSCrt is the Secret data key for a TLS certificate.
	KeyTLSCrt = "tls.crt"
	// KeyTLSKey is the Secret data key for a TLS private key.
	KeyTLSKey = "tls.key"
	// KeySAPub is the Secret data key for a service account public key.
	KeySAPub = "sa.pub"
	// KeySAKey is the Secret data key for a service account private key.
	KeySAKey = "sa.key"
)

// IdentitySpec describes certificate or key-pair material required by a layout.
type IdentitySpec struct {
	ID            IdentityID
	CommonName    string
	Organizations []string
	AltNames      certutil.AltNames
	Signer        SignerID
	Kind          IdentityKind
}

// MaterialRef points from a Secret data key to generated certificate material.
type MaterialRef struct {
	ID       IdentityID
	Part     MaterialPart
	Optional bool
}

// SecretSpec describes one Secret that should receive generated certificate material.
type SecretSpec struct {
	Name string
	Type corev1.SecretType
	Data map[string]MaterialRef
}

// KubeconfigSpec describes one component kubeconfig Secret and its client identity.
type KubeconfigSpec struct {
	Name        string
	ClientRef   IdentityID
	UserName    string
	ClusterName string
}

// ComponentName identifies a Karmada control-plane component in a certificate plan.
type ComponentName string

// Component constants identify Karmada components that consume certificate plans.
const (
	ComponentEtcd                  ComponentName = "etcd"
	ComponentAPIServer             ComponentName = "karmada-apiserver"
	ComponentKubeControllerManager ComponentName = "kube-controller-manager"
	ComponentScheduler             ComponentName = "karmada-scheduler"
	ComponentControllerManager     ComponentName = "karmada-controller-manager"
	ComponentWebhook               ComponentName = "karmada-webhook"
	ComponentAggregatedAPIServer   ComponentName = "karmada-aggregated-apiserver"
	ComponentDescheduler           ComponentName = "karmada-descheduler"
	ComponentSearch                ComponentName = "karmada-search"
	ComponentMetricsAdapter        ComponentName = "karmada-metrics-adapter"
)

// VolumeSpec describes a Secret-backed volume required by a component.
type VolumeSpec struct {
	Name       string
	SecretName string
}

// VolumeMountSpec describes where a component mounts certificate material.
type VolumeMountSpec struct {
	Name      string
	MountPath string
	ReadOnly  bool
}

// ComponentPlan describes certificate volumes, mounts, and command paths for a component.
type ComponentPlan struct {
	Volumes      []VolumeSpec
	VolumeMounts []VolumeMountSpec
	Paths        map[PathRole]string
}

// Plan describes all generated certificate material and distribution targets for a layout.
type Plan struct {
	Layout           string
	Identities       []IdentitySpec
	Secrets          []SecretSpec
	Kubeconfigs      []KubeconfigSpec
	Components       map[ComponentName]ComponentPlan
	CertificateNames []string
}
