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
	"fmt"
	"path/filepath"
	"strings"

	corev1 "k8s.io/api/core/v1"

	"github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/options"
	globaloptions "github.com/karmada-io/karmada/pkg/karmadactl/options"
	"github.com/karmada-io/karmada/pkg/karmadactl/util"
	"github.com/karmada-io/karmada/pkg/util/names"
)

const (
	karmadaCertsVolumeMountPath                 = "/etc/karmada/pki"
	karmadaConfigVolumeName                     = "karmada-config"
	karmadaConfigVolumeMountPath                = "/etc/karmada/config"
	serverCertVolumeName                        = "server-cert"
	serverCertVolumeMountPath                   = "/etc/karmada/pki/server"
	etcdClientCertVolumeName                    = "etcd-client-cert"
	etcdClientCertVolumeMountPath               = "/etc/karmada/pki/etcd-client"
	frontProxyClientCertVolumeName              = "front-proxy-client-cert"
	frontProxyClientCertVolumeMountPath         = "/etc/karmada/pki/front-proxy-client"
	serviceAccountKeyPairVolumeName             = "service-account-key-pair"
	serviceAccountKeyPairVolumeMountPath        = "/etc/karmada/pki/service-account-key-pair"
	caCertVolumeName                            = "ca-cert"
	caCertVolumeMountPath                       = "/etc/karmada/pki/ca"
	schedulerEstimatorClientCertVolumeName      = "scheduler-estimator-client-cert"
	schedulerEstimatorClientCertVolumeMountPath = "/etc/karmada/pki/scheduler-estimator-client"
	webhookCertVolumeName                       = "karmada-webhook-cert"
	webhookCertVolumeMountPath                  = "/var/serving-cert"
	etcdCertVolumeName                          = "etcd-cert"
)

// Secret name constants identify Kubernetes Secret objects, not credential
// values. Some names intentionally end with "-cert" to match existing deploy
// manifests and naming conventions.
const (
	SecretAPIServerServer               = "karmada-apiserver-cert"
	SecretAPIServerEtcdClient           = "karmada-apiserver-etcd-client-cert"
	SecretAPIServerFrontProxyClient     = "karmada-apiserver-front-proxy-client-cert"
	SecretAPIServerServiceAccountKeys   = "karmada-apiserver-service-account-key-pair"
	SecretAggregatedAPIServerServer     = "karmada-aggregated-apiserver-cert"
	SecretAggregatedAPIServerEtcdClient = "karmada-aggregated-apiserver-etcd-client-cert"
	SecretKubeControllerManagerCA       = "kube-controller-manager-ca-cert"
	SecretKubeControllerManagerSAKeys   = "kube-controller-manager-service-account-key-pair"
	SecretSchedulerEstimatorClient      = "karmada-scheduler-scheduler-estimator-client-cert"
	SecretDeschedulerEstimatorClient    = "karmada-descheduler-scheduler-estimator-client-cert" // #nosec G101 -- Kubernetes Secret object name, not credential material.
	SecretEtcdServer                    = "etcd-cert"                                           // #nosec G101 -- Kubernetes Secret object name, not credential material.
	SecretEtcdClient                    = "etcd-etcd-client-cert"                               // #nosec G101 -- Kubernetes Secret object name, not credential material.
	SecretWebhook                       = "karmada-webhook-cert"                                // #nosec G101 -- Kubernetes Secret object name, not credential material.
)

// NewPlan builds a certificate distribution plan for the requested Secret layout.
func NewPlan(layout string, externalEtcd bool) (*Plan, error) {
	switch strings.ToLower(layout) {
	case "", LayoutLegacy:
		return legacyPlan(externalEtcd), nil
	case LayoutSplit:
		return splitPlan(externalEtcd), nil
	default:
		return nil, fmt.Errorf("unsupported secret layout %q", layout)
	}
}

// SupportedLayouts returns the Secret layouts accepted by karmadactl init.
func SupportedLayouts() []string {
	return []string{LayoutLegacy, LayoutSplit}
}

// NormalizeLayout converts empty or unknown layout values to the legacy layout.
func NormalizeLayout(layout string) string {
	if strings.EqualFold(layout, LayoutSplit) {
		return LayoutSplit
	}
	return LayoutLegacy
}

func legacyPlan(externalEtcd bool) *Plan {
	certNames := legacyCertificateNames()

	return &Plan{
		Layout:           LayoutLegacy,
		Identities:       legacyIdentities(externalEtcd),
		Secrets:          legacySecrets(certNames),
		Kubeconfigs:      legacyKubeconfigs(),
		CertificateNames: certNames,
		Components: map[ComponentName]ComponentPlan{
			ComponentEtcd:                  certOnlyComponent(etcdCertVolumeName, SecretEtcdServer, karmadaCertsVolumeMountPath, legacyEtcdPaths()),
			ComponentAPIServer:             certOnlyComponent(globaloptions.KarmadaCertsName, globaloptions.KarmadaCertsName, karmadaCertsVolumeMountPath, legacyAPIServerPaths()),
			ComponentKubeControllerManager: configAndCertComponent(names.KubeControllerManagerComponentName, globaloptions.KarmadaCertsName, karmadaCertsVolumeMountPath, legacyKubeControllerManagerPaths()),
			ComponentScheduler:             configAndCertComponent(names.KarmadaSchedulerComponentName, globaloptions.KarmadaCertsName, karmadaCertsVolumeMountPath, legacySchedulerPaths()),
			ComponentControllerManager:     configOnlyComponent(names.KarmadaControllerManagerComponentName),
			ComponentWebhook: {
				Volumes: []VolumeSpec{
					configVolume(names.KarmadaWebhookComponentName),
					{Name: webhookCertVolumeName, SecretName: SecretWebhook},
				},
				VolumeMounts: []VolumeMountSpec{
					configVolumeMount(),
					{Name: webhookCertVolumeName, MountPath: webhookCertVolumeMountPath, ReadOnly: true},
				},
				Paths: map[PathRole]string{PathWebhookCertDir: webhookCertVolumeMountPath},
			},
			ComponentAggregatedAPIServer: configAndCertComponent(names.KarmadaAggregatedAPIServerComponentName, globaloptions.KarmadaCertsName, karmadaCertsVolumeMountPath, legacyAggregatedAPIServerPaths()),
		},
	}
}

func splitPlan(externalEtcd bool) *Plan {
	return &Plan{
		Layout:           LayoutSplit,
		Identities:       splitIdentities(externalEtcd),
		Secrets:          splitSecrets(externalEtcd),
		Kubeconfigs:      splitKubeconfigs(),
		CertificateNames: splitCertificateNames(externalEtcd),
		Components: map[ComponentName]ComponentPlan{
			ComponentEtcd: {
				Volumes: []VolumeSpec{
					{Name: serverCertVolumeName, SecretName: SecretEtcdServer},
					{Name: etcdClientCertVolumeName, SecretName: SecretEtcdClient},
				},
				VolumeMounts: []VolumeMountSpec{
					{Name: serverCertVolumeName, MountPath: serverCertVolumeMountPath, ReadOnly: true},
					{Name: etcdClientCertVolumeName, MountPath: etcdClientCertVolumeMountPath, ReadOnly: true},
				},
				Paths: splitEtcdPaths(),
			},
			ComponentAPIServer: {
				Volumes: []VolumeSpec{
					{Name: serverCertVolumeName, SecretName: SecretAPIServerServer},
					{Name: etcdClientCertVolumeName, SecretName: SecretAPIServerEtcdClient},
					{Name: frontProxyClientCertVolumeName, SecretName: SecretAPIServerFrontProxyClient},
					{Name: serviceAccountKeyPairVolumeName, SecretName: SecretAPIServerServiceAccountKeys},
				},
				VolumeMounts: []VolumeMountSpec{
					{Name: serverCertVolumeName, MountPath: serverCertVolumeMountPath, ReadOnly: true},
					{Name: etcdClientCertVolumeName, MountPath: etcdClientCertVolumeMountPath, ReadOnly: true},
					{Name: frontProxyClientCertVolumeName, MountPath: frontProxyClientCertVolumeMountPath, ReadOnly: true},
					{Name: serviceAccountKeyPairVolumeName, MountPath: serviceAccountKeyPairVolumeMountPath, ReadOnly: true},
				},
				Paths: splitAPIServerPaths(),
			},
			ComponentKubeControllerManager: {
				Volumes: []VolumeSpec{
					configVolume(names.KubeControllerManagerComponentName),
					{Name: caCertVolumeName, SecretName: SecretKubeControllerManagerCA},
					{Name: serviceAccountKeyPairVolumeName, SecretName: SecretKubeControllerManagerSAKeys},
				},
				VolumeMounts: []VolumeMountSpec{
					configVolumeMount(),
					{Name: caCertVolumeName, MountPath: caCertVolumeMountPath, ReadOnly: true},
					{Name: serviceAccountKeyPairVolumeName, MountPath: serviceAccountKeyPairVolumeMountPath, ReadOnly: true},
				},
				Paths: splitKubeControllerManagerPaths(),
			},
			ComponentScheduler: {
				Volumes: []VolumeSpec{
					configVolume(names.KarmadaSchedulerComponentName),
					{Name: schedulerEstimatorClientCertVolumeName, SecretName: SecretSchedulerEstimatorClient},
				},
				VolumeMounts: []VolumeMountSpec{
					configVolumeMount(),
					{Name: schedulerEstimatorClientCertVolumeName, MountPath: schedulerEstimatorClientCertVolumeMountPath, ReadOnly: true},
				},
				Paths: splitSchedulerPaths(),
			},
			ComponentControllerManager:   configOnlyComponent(names.KarmadaControllerManagerComponentName),
			ComponentWebhook:             splitWebhookComponent(),
			ComponentAggregatedAPIServer: splitAggregatedAPIServerComponent(),
		},
	}
}

func legacyIdentities(externalEtcd bool) []IdentitySpec {
	identities := []IdentitySpec{
		caIdentity(RootCA, "karmada"),
		certIdentity(AdminClient, RootCA, "system:admin", []string{"system:masters"}),
		certIdentity(APIServerServer, RootCA, "karmada-apiserver", nil),
		caIdentity(FrontProxyCA, "front-proxy-ca"),
		certIdentity(FrontProxyClient, FrontProxyCA, "front-proxy-client", nil),
	}
	if !externalEtcd {
		identities = append(identities,
			caIdentity(EtcdCA, "etcd-ca"),
			certIdentity(EtcdServer, EtcdCA, "karmada-etcd-server", nil),
			certIdentity(EtcdClient, EtcdCA, "karmada-etcd-client", nil),
		)
	}
	return identities
}

func splitIdentities(externalEtcd bool) []IdentitySpec {
	identities := []IdentitySpec{
		caIdentity(RootCA, "karmada"),
		certIdentity(AdminClient, RootCA, "system:admin", []string{"system:masters"}),
		certIdentity(APIServerServer, RootCA, "karmada-apiserver", nil),
		certIdentity(AggregatedAPIServerServer, RootCA, "system:karmada:karmada-aggregated-apiserver", nil),
		certIdentity(WebhookServer, RootCA, "system:karmada:karmada-webhook", nil),
		certIdentity(ControllerManagerClient, RootCA, "system:karmada:karmada-controller-manager", []string{"system:masters"}),
		certIdentity(SchedulerClient, RootCA, "system:karmada:karmada-scheduler", []string{"system:masters"}),
		certIdentity(AggregatedAPIServerClient, RootCA, "system:karmada:karmada-aggregated-apiserver", []string{"system:masters"}),
		certIdentity(WebhookClient, RootCA, "system:karmada:karmada-webhook", []string{"system:masters"}),
		certIdentity(KubeControllerManagerClient, RootCA, "system:karmada:kube-controller-manager", []string{"system:masters"}),
		certIdentity(DeschedulerClient, RootCA, "system:karmada:karmada-descheduler", []string{"system:masters"}),
		certIdentity(SearchClient, RootCA, "system:karmada:karmada-search", []string{"system:masters"}),
		certIdentity(MetricsAdapterClient, RootCA, "system:karmada:karmada-metrics-adapter", []string{"system:masters"}),
		certIdentity(SchedulerEstimatorClient, RootCA, "system:karmada:karmada-scheduler-grpc", []string{"system:masters"}),
		certIdentity(DeschedulerEstimatorClient, RootCA, "system:karmada:karmada-descheduler-grpc", []string{"system:masters"}),
		caIdentity(FrontProxyCA, "front-proxy-ca"),
		certIdentity(FrontProxyClient, FrontProxyCA, "front-proxy-client", nil),
		{ID: APIServerServiceAccountKeyPair, Kind: KindKeyPair},
	}
	if !externalEtcd {
		identities = append(identities,
			caIdentity(EtcdCA, "etcd-ca"),
			certIdentity(EtcdServer, EtcdCA, "karmada-etcd-server", nil),
			certIdentity(EtcdClient, EtcdCA, "karmada-etcd-client", nil),
			certIdentity(APIServerEtcdClient, EtcdCA, "system:karmada:karmada-apiserver-etcd-client", []string{"system:masters"}),
			certIdentity(AggregatedAPIServerEtcdClient, EtcdCA, "system:karmada:karmada-aggregated-apiserver-etcd-client", []string{"system:masters"}),
		)
	}
	return identities
}

func legacyCertificateNames() []string {
	return []string{
		string(RootCA),
		string(EtcdCA),
		string(EtcdServer),
		string(EtcdClient),
		string(AdminClient),
		string(APIServerServer),
		string(FrontProxyCA),
		string(FrontProxyClient),
	}
}

func splitCertificateNames(externalEtcd bool) []string {
	certNames := []string{
		string(RootCA),
		string(EtcdCA),
		string(EtcdClient),
		string(AdminClient),
		string(APIServerServer),
		string(FrontProxyCA),
		string(FrontProxyClient),
		string(AggregatedAPIServerServer),
		string(WebhookServer),
		string(ControllerManagerClient),
		string(SchedulerClient),
		string(AggregatedAPIServerClient),
		string(WebhookClient),
		string(KubeControllerManagerClient),
		string(DeschedulerClient),
		string(SearchClient),
		string(MetricsAdapterClient),
		string(SchedulerEstimatorClient),
		string(DeschedulerEstimatorClient),
		string(APIServerServiceAccountKeyPair),
	}
	if !externalEtcd {
		certNames = append(certNames,
			string(EtcdServer),
			string(APIServerEtcdClient),
			string(AggregatedAPIServerEtcdClient),
		)
	}
	return certNames
}

func caIdentity(id IdentityID, cn string) IdentitySpec {
	return IdentitySpec{ID: id, CommonName: cn, Kind: KindCertificate}
}

func certIdentity(id IdentityID, signer IdentityID, cn string, org []string) IdentitySpec {
	return IdentitySpec{ID: id, CommonName: cn, Organizations: org, Signer: SignerID(signer), Kind: KindCertificate}
}

func legacySecrets(certNames []string) []SecretSpec {
	etcdSecret := SecretSpec{Name: SecretEtcdServer, Type: corev1.SecretTypeOpaque, Data: map[string]MaterialRef{
		fileKey(EtcdCA, PartCert):     {ID: EtcdCA, Part: PartCert},
		fileKey(EtcdCA, PartKey):      {ID: EtcdCA, Part: PartKey},
		fileKey(EtcdServer, PartCert): {ID: EtcdServer, Part: PartCert},
		fileKey(EtcdServer, PartKey):  {ID: EtcdServer, Part: PartKey},
	}}
	karmadaCert := SecretSpec{Name: globaloptions.KarmadaCertsName, Type: corev1.SecretTypeOpaque, Data: map[string]MaterialRef{}}
	for _, name := range certNames {
		id := IdentityID(name)
		karmadaCert.Data[fileKey(id, PartCert)] = MaterialRef{ID: id, Part: PartCert}
		karmadaCert.Data[fileKey(id, PartKey)] = MaterialRef{ID: id, Part: PartKey}
	}
	webhookSecret := SecretSpec{Name: SecretWebhook, Type: corev1.SecretTypeOpaque, Data: map[string]MaterialRef{
		KeyTLSCrt: {ID: AdminClient, Part: PartCert},
		KeyTLSKey: {ID: AdminClient, Part: PartKey},
	}}
	return []SecretSpec{etcdSecret, karmadaCert, webhookSecret}
}

func splitSecrets(externalEtcd bool) []SecretSpec {
	apiserverEtcdClient := APIServerEtcdClient
	aggregatedAPIServerEtcdClient := AggregatedAPIServerEtcdClient
	if externalEtcd {
		apiserverEtcdClient = EtcdClient
		aggregatedAPIServerEtcdClient = EtcdClient
	}

	secrets := []SecretSpec{
		tlsSecret(SecretAPIServerServer, RootCA, APIServerServer),
		tlsSecret(SecretAPIServerEtcdClient, EtcdCA, apiserverEtcdClient),
		tlsSecret(SecretAPIServerFrontProxyClient, FrontProxyCA, FrontProxyClient),
		keyPairSecret(SecretAPIServerServiceAccountKeys, APIServerServiceAccountKeyPair),
		tlsSecret(SecretAggregatedAPIServerServer, RootCA, AggregatedAPIServerServer),
		tlsSecret(SecretAggregatedAPIServerEtcdClient, EtcdCA, aggregatedAPIServerEtcdClient),
		tlsSecret(SecretKubeControllerManagerCA, RootCA, RootCA),
		keyPairSecret(SecretKubeControllerManagerSAKeys, APIServerServiceAccountKeyPair),
		tlsSecret(SecretSchedulerEstimatorClient, RootCA, SchedulerEstimatorClient),
		tlsSecret(SecretDeschedulerEstimatorClient, RootCA, DeschedulerEstimatorClient),
		tlsSecret(SecretWebhook, RootCA, WebhookServer),
		legacyCompatibleKarmadaCert(externalEtcd),
	}
	if !externalEtcd {
		secrets = append(secrets,
			tlsSecret(SecretEtcdServer, EtcdCA, EtcdServer),
			tlsSecret(SecretEtcdClient, EtcdCA, EtcdClient),
		)
	}
	return secrets
}

func tlsSecret(name string, caID, certID IdentityID) SecretSpec {
	return SecretSpec{Name: name, Type: corev1.SecretTypeTLS, Data: map[string]MaterialRef{
		KeyCACrt:  {ID: caID, Part: PartCert},
		KeyTLSCrt: {ID: certID, Part: PartCert},
		KeyTLSKey: {ID: certID, Part: PartKey},
	}}
}

func keyPairSecret(name string, id IdentityID) SecretSpec {
	return SecretSpec{Name: name, Type: corev1.SecretTypeOpaque, Data: map[string]MaterialRef{
		KeySAPub: {ID: id, Part: PartPublicKey},
		KeySAKey: {ID: id, Part: PartKey},
	}}
}

func legacyCompatibleKarmadaCert(externalEtcd bool) SecretSpec {
	etcdCAKeyRef := MaterialRef{ID: EtcdCA, Part: PartKey}
	if externalEtcd {
		etcdCAKeyRef.Optional = true
	}
	secret := SecretSpec{Name: globaloptions.KarmadaCertsName, Type: corev1.SecretTypeOpaque, Data: map[string]MaterialRef{
		fileKey(RootCA, PartCert):           {ID: RootCA, Part: PartCert},
		fileKey(RootCA, PartKey):            {ID: RootCA, Part: PartKey},
		fileKey(EtcdCA, PartCert):           {ID: EtcdCA, Part: PartCert},
		fileKey(EtcdCA, PartKey):            etcdCAKeyRef,
		fileKey(EtcdClient, PartCert):       {ID: EtcdClient, Part: PartCert},
		fileKey(EtcdClient, PartKey):        {ID: EtcdClient, Part: PartKey},
		fileKey(AdminClient, PartCert):      {ID: AdminClient, Part: PartCert},
		fileKey(AdminClient, PartKey):       {ID: AdminClient, Part: PartKey},
		fileKey(APIServerServer, PartCert):  {ID: APIServerServer, Part: PartCert},
		fileKey(APIServerServer, PartKey):   {ID: APIServerServer, Part: PartKey},
		fileKey(FrontProxyCA, PartCert):     {ID: FrontProxyCA, Part: PartCert},
		fileKey(FrontProxyCA, PartKey):      {ID: FrontProxyCA, Part: PartKey},
		fileKey(FrontProxyClient, PartCert): {ID: FrontProxyClient, Part: PartCert},
		fileKey(FrontProxyClient, PartKey):  {ID: FrontProxyClient, Part: PartKey},
	}}
	if externalEtcd {
		secret.Data[fileKey(EtcdServer, PartCert)] = MaterialRef{ID: EtcdServer, Part: PartCert, Optional: true}
		secret.Data[fileKey(EtcdServer, PartKey)] = MaterialRef{ID: EtcdServer, Part: PartKey, Optional: true}
	} else {
		secret.Data[fileKey(EtcdServer, PartCert)] = MaterialRef{ID: EtcdServer, Part: PartCert}
		secret.Data[fileKey(EtcdServer, PartKey)] = MaterialRef{ID: EtcdServer, Part: PartKey}
	}
	return secret
}

func legacyKubeconfigs() []KubeconfigSpec {
	configs := make([]KubeconfigSpec, 0, len(karmadaConfigComponents()))
	for _, component := range karmadaConfigComponents() {
		configs = append(configs, KubeconfigSpec{
			Name:        util.KarmadaConfigName(component),
			ClientRef:   AdminClient,
			UserName:    options.UserName,
			ClusterName: options.UserName,
		})
	}
	return configs
}

func splitKubeconfigs() []KubeconfigSpec {
	clientByComponent := map[string]IdentityID{
		names.KarmadaAggregatedAPIServerComponentName: AggregatedAPIServerClient,
		names.KarmadaControllerManagerComponentName:   ControllerManagerClient,
		names.KubeControllerManagerComponentName:      KubeControllerManagerClient,
		names.KarmadaSchedulerComponentName:           SchedulerClient,
		names.KarmadaDeschedulerComponentName:         DeschedulerClient,
		names.KarmadaMetricsAdapterComponentName:      MetricsAdapterClient,
		names.KarmadaSearchComponentName:              SearchClient,
		names.KarmadaWebhookComponentName:             WebhookClient,
	}
	configs := make([]KubeconfigSpec, 0, len(clientByComponent))
	for _, component := range karmadaConfigComponents() {
		configs = append(configs, KubeconfigSpec{
			Name:        util.KarmadaConfigName(component),
			ClientRef:   clientByComponent[component],
			UserName:    options.ClusterName,
			ClusterName: options.ClusterName,
		})
	}
	return configs
}

func karmadaConfigComponents() []string {
	return []string{
		names.KarmadaAggregatedAPIServerComponentName,
		names.KarmadaControllerManagerComponentName,
		names.KubeControllerManagerComponentName,
		names.KarmadaSchedulerComponentName,
		names.KarmadaDeschedulerComponentName,
		names.KarmadaMetricsAdapterComponentName,
		names.KarmadaSearchComponentName,
		names.KarmadaWebhookComponentName,
	}
}

func fileKey(id IdentityID, part MaterialPart) string {
	suffix := "crt"
	if part == PartKey {
		suffix = "key"
	}
	return fmt.Sprintf("%s.%s", id, suffix)
}

func configOnlyComponent(component string) ComponentPlan {
	return ComponentPlan{
		Volumes:      []VolumeSpec{configVolume(component)},
		VolumeMounts: []VolumeMountSpec{configVolumeMount()},
		Paths:        map[PathRole]string{},
	}
}

func certOnlyComponent(volumeName, secretName, mountPath string, paths map[PathRole]string) ComponentPlan {
	return ComponentPlan{
		Volumes:      []VolumeSpec{{Name: volumeName, SecretName: secretName}},
		VolumeMounts: []VolumeMountSpec{{Name: volumeName, MountPath: mountPath, ReadOnly: true}},
		Paths:        paths,
	}
}

func configAndCertComponent(component, secretName, mountPath string, paths map[PathRole]string) ComponentPlan {
	return ComponentPlan{
		Volumes:      []VolumeSpec{configVolume(component), {Name: globaloptions.KarmadaCertsName, SecretName: secretName}},
		VolumeMounts: []VolumeMountSpec{configVolumeMount(), {Name: globaloptions.KarmadaCertsName, MountPath: mountPath, ReadOnly: true}},
		Paths:        paths,
	}
}

func splitWebhookComponent() ComponentPlan {
	return ComponentPlan{
		Volumes: []VolumeSpec{
			configVolume(names.KarmadaWebhookComponentName),
			{Name: webhookCertVolumeName, SecretName: SecretWebhook},
		},
		VolumeMounts: []VolumeMountSpec{
			configVolumeMount(),
			{Name: webhookCertVolumeName, MountPath: webhookCertVolumeMountPath, ReadOnly: true},
		},
		Paths: map[PathRole]string{PathWebhookCertDir: webhookCertVolumeMountPath},
	}
}

func splitAggregatedAPIServerComponent() ComponentPlan {
	return ComponentPlan{
		Volumes: []VolumeSpec{
			configVolume(names.KarmadaAggregatedAPIServerComponentName),
			{Name: serverCertVolumeName, SecretName: SecretAggregatedAPIServerServer},
			{Name: etcdClientCertVolumeName, SecretName: SecretAggregatedAPIServerEtcdClient},
		},
		VolumeMounts: []VolumeMountSpec{
			configVolumeMount(),
			{Name: serverCertVolumeName, MountPath: serverCertVolumeMountPath, ReadOnly: true},
			{Name: etcdClientCertVolumeName, MountPath: etcdClientCertVolumeMountPath, ReadOnly: true},
		},
		Paths: splitAggregatedAPIServerPaths(),
	}
}

func configVolume(component string) VolumeSpec {
	return VolumeSpec{Name: karmadaConfigVolumeName, SecretName: util.KarmadaConfigName(component)}
}

func configVolumeMount() VolumeMountSpec {
	return VolumeMountSpec{Name: karmadaConfigVolumeName, MountPath: karmadaConfigVolumeMountPath, ReadOnly: true}
}

func p(dir, file string) string {
	return filepath.Join(dir, file)
}

func legacyAPIServerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathClientCAFile:                 p(karmadaCertsVolumeMountPath, "ca.crt"),
		PathEtcdCAFile:                   p(karmadaCertsVolumeMountPath, "etcd-ca.crt"),
		PathEtcdCertFile:                 p(karmadaCertsVolumeMountPath, "etcd-client.crt"),
		PathEtcdKeyFile:                  p(karmadaCertsVolumeMountPath, "etcd-client.key"),
		PathServiceAccountPublicKeyFile:  p(karmadaCertsVolumeMountPath, "karmada.key"),
		PathServiceAccountPrivateKeyFile: p(karmadaCertsVolumeMountPath, "karmada.key"),
		PathProxyClientCertFile:          p(karmadaCertsVolumeMountPath, "front-proxy-client.crt"),
		PathProxyClientKeyFile:           p(karmadaCertsVolumeMountPath, "front-proxy-client.key"),
		PathRequestHeaderClientCAFile:    p(karmadaCertsVolumeMountPath, "front-proxy-ca.crt"),
		PathTLSCertFile:                  p(karmadaCertsVolumeMountPath, "apiserver.crt"),
		PathTLSKeyFile:                   p(karmadaCertsVolumeMountPath, "apiserver.key"),
	}
}

func splitAPIServerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathClientCAFile:                 p(serverCertVolumeMountPath, KeyCACrt),
		PathEtcdCAFile:                   p(etcdClientCertVolumeMountPath, KeyCACrt),
		PathEtcdCertFile:                 p(etcdClientCertVolumeMountPath, KeyTLSCrt),
		PathEtcdKeyFile:                  p(etcdClientCertVolumeMountPath, KeyTLSKey),
		PathServiceAccountPublicKeyFile:  p(serviceAccountKeyPairVolumeMountPath, KeySAPub),
		PathServiceAccountPrivateKeyFile: p(serviceAccountKeyPairVolumeMountPath, KeySAKey),
		PathProxyClientCertFile:          p(frontProxyClientCertVolumeMountPath, KeyTLSCrt),
		PathProxyClientKeyFile:           p(frontProxyClientCertVolumeMountPath, KeyTLSKey),
		PathRequestHeaderClientCAFile:    p(frontProxyClientCertVolumeMountPath, KeyCACrt),
		PathTLSCertFile:                  p(serverCertVolumeMountPath, KeyTLSCrt),
		PathTLSKeyFile:                   p(serverCertVolumeMountPath, KeyTLSKey),
	}
}

func legacyKubeControllerManagerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathClientCAFile:                 p(karmadaCertsVolumeMountPath, "ca.crt"),
		PathClusterSigningCertFile:       p(karmadaCertsVolumeMountPath, "ca.crt"),
		PathClusterSigningKeyFile:        p(karmadaCertsVolumeMountPath, "ca.key"),
		PathRootCAFile:                   p(karmadaCertsVolumeMountPath, "ca.crt"),
		PathServiceAccountPrivateKeyFile: p(karmadaCertsVolumeMountPath, "karmada.key"),
	}
}

func splitKubeControllerManagerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathClientCAFile:                 p(caCertVolumeMountPath, KeyTLSCrt),
		PathClusterSigningCertFile:       p(caCertVolumeMountPath, KeyTLSCrt),
		PathClusterSigningKeyFile:        p(caCertVolumeMountPath, KeyTLSKey),
		PathRootCAFile:                   p(caCertVolumeMountPath, KeyTLSCrt),
		PathServiceAccountPrivateKeyFile: p(serviceAccountKeyPairVolumeMountPath, KeySAKey),
	}
}

func legacySchedulerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathSchedulerEstimatorCAFile:   p(karmadaCertsVolumeMountPath, "ca.crt"),
		PathSchedulerEstimatorCertFile: p(karmadaCertsVolumeMountPath, "karmada.crt"),
		PathSchedulerEstimatorKeyFile:  p(karmadaCertsVolumeMountPath, "karmada.key"),
	}
}

func splitSchedulerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathSchedulerEstimatorCAFile:   p(schedulerEstimatorClientCertVolumeMountPath, KeyCACrt),
		PathSchedulerEstimatorCertFile: p(schedulerEstimatorClientCertVolumeMountPath, KeyTLSCrt),
		PathSchedulerEstimatorKeyFile:  p(schedulerEstimatorClientCertVolumeMountPath, KeyTLSKey),
	}
}

func legacyAggregatedAPIServerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathEtcdCAFile:   p(karmadaCertsVolumeMountPath, "etcd-ca.crt"),
		PathEtcdCertFile: p(karmadaCertsVolumeMountPath, "etcd-client.crt"),
		PathEtcdKeyFile:  p(karmadaCertsVolumeMountPath, "etcd-client.key"),
		PathTLSCertFile:  p(karmadaCertsVolumeMountPath, "karmada.crt"),
		PathTLSKeyFile:   p(karmadaCertsVolumeMountPath, "karmada.key"),
	}
}

func splitAggregatedAPIServerPaths() map[PathRole]string {
	return map[PathRole]string{
		PathEtcdCAFile:   p(etcdClientCertVolumeMountPath, KeyCACrt),
		PathEtcdCertFile: p(etcdClientCertVolumeMountPath, KeyTLSCrt),
		PathEtcdKeyFile:  p(etcdClientCertVolumeMountPath, KeyTLSKey),
		PathTLSCertFile:  p(serverCertVolumeMountPath, KeyTLSCrt),
		PathTLSKeyFile:   p(serverCertVolumeMountPath, KeyTLSKey),
	}
}

func legacyEtcdPaths() map[PathRole]string {
	return map[PathRole]string{
		PathTLSCertFile:      p(karmadaCertsVolumeMountPath, "etcd-server.crt"),
		PathTLSKeyFile:       p(karmadaCertsVolumeMountPath, "etcd-server.key"),
		PathClientCAFile:     p(karmadaCertsVolumeMountPath, "etcd-ca.crt"),
		PathEtcdPeerCAFile:   p(karmadaCertsVolumeMountPath, "etcd-ca.crt"),
		PathEtcdPeerCertFile: p(karmadaCertsVolumeMountPath, "etcd-server.crt"),
		PathEtcdPeerKeyFile:  p(karmadaCertsVolumeMountPath, "etcd-server.key"),
	}
}

func splitEtcdPaths() map[PathRole]string {
	return map[PathRole]string{
		PathTLSCertFile:      p(serverCertVolumeMountPath, KeyTLSCrt),
		PathTLSKeyFile:       p(serverCertVolumeMountPath, KeyTLSKey),
		PathClientCAFile:     p(serverCertVolumeMountPath, KeyCACrt),
		PathEtcdPeerCAFile:   p(serverCertVolumeMountPath, KeyCACrt),
		PathEtcdPeerCertFile: p(serverCertVolumeMountPath, KeyTLSCrt),
		PathEtcdPeerKeyFile:  p(serverCertVolumeMountPath, KeyTLSKey),
	}
}
