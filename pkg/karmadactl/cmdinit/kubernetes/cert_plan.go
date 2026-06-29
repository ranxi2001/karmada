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

package kubernetes

import (
	"crypto"
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"
	"path/filepath"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/klog/v2"

	"github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/cert"
	"github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/certmanager"
	"github.com/karmada-io/karmada/pkg/karmadactl/cmdinit/utils"
)

const publicKeyBlockType = "PUBLIC KEY"

func (i *CommandInitOption) certificatePlan() (*certmanager.Plan, error) {
	return certmanager.NewPlan(i.SecretLayout, i.isExternalEtcdProvided())
}

func (i *CommandInitOption) componentPlan(component certmanager.ComponentName) certmanager.ComponentPlan {
	plan, err := i.certificatePlan()
	if err != nil {
		klog.Warningf("failed to build certificate plan: %v", err)
		return certmanager.ComponentPlan{}
	}
	return plan.Components[component]
}

func (i *CommandInitOption) componentPaths(component certmanager.ComponentName) map[certmanager.PathRole]string {
	return i.componentPlan(component).Paths
}

func (i *CommandInitOption) componentVolumes(component certmanager.ComponentName) []corev1.Volume {
	plan := i.componentPlan(component)
	volumes := make([]corev1.Volume, 0, len(plan.Volumes))
	for _, volume := range plan.Volumes {
		volumes = append(volumes, corev1.Volume{
			Name: volume.Name,
			VolumeSource: corev1.VolumeSource{
				Secret: &corev1.SecretVolumeSource{
					SecretName: volume.SecretName,
				},
			},
		})
	}
	return volumes
}

func (i *CommandInitOption) componentVolumeMounts(component certmanager.ComponentName) []corev1.VolumeMount {
	plan := i.componentPlan(component)
	mounts := make([]corev1.VolumeMount, 0, len(plan.VolumeMounts))
	for _, mount := range plan.VolumeMounts {
		mounts = append(mounts, corev1.VolumeMount{
			Name:      mount.Name,
			MountPath: mount.MountPath,
			ReadOnly:  mount.ReadOnly,
		})
	}
	return mounts
}

func (i *CommandInitOption) genPlanCerts(plan *certmanager.Plan) error {
	if err := i.genCerts(); err != nil {
		return err
	}
	if certmanager.NormalizeLayout(plan.Layout) == certmanager.LayoutLegacy {
		return nil
	}

	caCert, caKey, err := loadCertAndKey(i.KarmadaPkiPath, string(certmanager.RootCA))
	if err != nil {
		return err
	}
	frontProxyCACert, frontProxyCAKey, err := loadCertAndKey(i.KarmadaPkiPath, string(certmanager.FrontProxyCA))
	if err != nil {
		return err
	}

	signerCerts := map[certmanager.SignerID]*x509.Certificate{
		certmanager.SignerID(certmanager.RootCA):       caCert,
		certmanager.SignerID(certmanager.FrontProxyCA): frontProxyCACert,
	}
	signerKeys := map[certmanager.SignerID]crypto.Signer{
		certmanager.SignerID(certmanager.RootCA):       caKey,
		certmanager.SignerID(certmanager.FrontProxyCA): frontProxyCAKey,
	}
	if !i.isExternalEtcdProvided() {
		etcdCACert, etcdCAKey, err := loadCertAndKey(i.KarmadaPkiPath, string(certmanager.EtcdCA))
		if err != nil {
			return err
		}
		signerCerts[certmanager.SignerID(certmanager.EtcdCA)] = etcdCACert
		signerKeys[certmanager.SignerID(certmanager.EtcdCA)] = etcdCAKey
	}

	notAfter := i.certificateNotAfter()
	for _, identity := range plan.Identities {
		if identity.Kind != certmanager.KindCertificate || isLegacyCertificate(identity.ID) {
			continue
		}
		caCert, ok := signerCerts[identity.Signer]
		if !ok {
			return fmt.Errorf("missing signer certificate %q for %q", identity.Signer, identity.ID)
		}
		caKey, ok := signerKeys[identity.Signer]
		if !ok {
			return fmt.Errorf("missing signer key %q for %q", identity.Signer, identity.ID)
		}
		altNames := identity.AltNames
		if needsKarmadaAltNames(identity.ID) {
			altNames = i.karmadaAltNames()
		}
		cfg := cert.NewCertConfig(identity.CommonName, identity.Organizations, altNames, &notAfter)
		signedCert, signedKey, err := cert.NewCertAndKey(caCert, caKey, cfg)
		if err != nil {
			return fmt.Errorf("failed to generate certificate %q: %w", identity.ID, err)
		}
		if err := cert.WriteCertAndKey(i.KarmadaPkiPath, string(identity.ID), signedCert, &signedKey); err != nil {
			return err
		}
	}

	return i.genKeyPairs(plan)
}

func (i *CommandInitOption) genKeyPairs(plan *certmanager.Plan) error {
	for _, identity := range plan.Identities {
		if identity.Kind != certmanager.KindKeyPair {
			continue
		}
		key, err := cert.GeneratePrivateKey(x509.RSA)
		if err != nil {
			return err
		}
		if err := cert.WriteKey(i.KarmadaPkiPath, string(identity.ID), key); err != nil {
			return err
		}
		publicKeyDER, err := x509.MarshalPKIXPublicKey(key.Public())
		if err != nil {
			return err
		}
		publicKeyPEM := pem.EncodeToMemory(&pem.Block{Type: publicKeyBlockType, Bytes: publicKeyDER})
		publicKeyPath := filepath.Join(i.KarmadaPkiPath, fmt.Sprintf("%s.pub", identity.ID))
		if err := os.WriteFile(publicKeyPath, publicKeyPEM, 0600); err != nil {
			return err
		}
	}
	return nil
}

func (i *CommandInitOption) readPlanCertificateData(plan *certmanager.Plan) error {
	i.CertAndKeyFileData = map[string][]byte{}
	identityKinds := map[certmanager.IdentityID]certmanager.IdentityKind{}
	for _, identity := range plan.Identities {
		identityKinds[identity.ID] = identity.Kind
	}

	for _, name := range plan.CertificateNames {
		if isExternalEtcdCert, err := i.readExternalEtcdCert(name); err != nil {
			return fmt.Errorf("read external etcd certificate failed, %s. %v", name, err)
		} else if isExternalEtcdCert {
			continue
		}

		id := certmanager.IdentityID(name)
		if identityKinds[id] == certmanager.KindKeyPair {
			if err := i.readKeyPairData(id); err != nil {
				return err
			}
			continue
		}
		if err := i.readCertAndKeyData(id); err != nil {
			return err
		}
	}
	return nil
}

func (i *CommandInitOption) readCertAndKeyData(id certmanager.IdentityID) error {
	name := string(id)
	certs, err := utils.FileToBytes(i.KarmadaPkiPath, fmt.Sprintf("%s.crt", name))
	if err != nil {
		return fmt.Errorf("'%s.crt' conversion failed. %v", name, err)
	}
	i.CertAndKeyFileData[fmt.Sprintf("%s.crt", name)] = certs

	key, err := utils.FileToBytes(i.KarmadaPkiPath, fmt.Sprintf("%s.key", name))
	if err != nil {
		return fmt.Errorf("'%s.key' conversion failed. %v", name, err)
	}
	i.CertAndKeyFileData[fmt.Sprintf("%s.key", name)] = key
	return nil
}

func (i *CommandInitOption) readKeyPairData(id certmanager.IdentityID) error {
	name := string(id)
	key, err := utils.FileToBytes(i.KarmadaPkiPath, fmt.Sprintf("%s.key", name))
	if err != nil {
		return fmt.Errorf("'%s.key' conversion failed. %v", name, err)
	}
	i.CertAndKeyFileData[fmt.Sprintf("%s.key", name)] = key

	publicKey, err := utils.FileToBytes(i.KarmadaPkiPath, fmt.Sprintf("%s.pub", name))
	if err != nil {
		return fmt.Errorf("'%s.pub' conversion failed. %v", name, err)
	}
	i.CertAndKeyFileData[fmt.Sprintf("%s.pub", name)] = publicKey
	return nil
}

func (i *CommandInitOption) materialData(ref certmanager.MaterialRef) ([]byte, error) {
	key := materialDataKey(ref)
	data, ok := i.CertAndKeyFileData[key]
	if !ok {
		if ref.Optional {
			return emptyByteSlice, nil
		}
		return nil, fmt.Errorf("missing certificate material %q", key)
	}
	return data, nil
}

func materialDataKey(ref certmanager.MaterialRef) string {
	switch ref.Part {
	case certmanager.PartCert:
		return fmt.Sprintf("%s.crt", ref.ID)
	case certmanager.PartKey:
		return fmt.Sprintf("%s.key", ref.ID)
	case certmanager.PartPublicKey:
		return fmt.Sprintf("%s.pub", ref.ID)
	default:
		return fmt.Sprintf("%s.%s", ref.ID, ref.Part)
	}
}

func loadCertAndKey(pkiPath, name string) (*x509.Certificate, crypto.Signer, error) {
	certificate, err := tls.LoadX509KeyPair(cert.PathForCert(pkiPath, name), cert.PathForKey(pkiPath, name))
	if err != nil {
		return nil, nil, err
	}
	certs, err := x509.ParseCertificate(certificate.Certificate[0])
	if err != nil {
		return nil, nil, err
	}
	key, ok := certificate.PrivateKey.(crypto.Signer)
	if !ok {
		return nil, nil, fmt.Errorf("private key %q does not implement crypto.Signer", name)
	}
	return certs, key, nil
}

func isLegacyCertificate(id certmanager.IdentityID) bool {
	switch id {
	case certmanager.RootCA,
		certmanager.EtcdCA,
		certmanager.EtcdServer,
		certmanager.EtcdClient,
		certmanager.AdminClient,
		certmanager.APIServerServer,
		certmanager.FrontProxyCA,
		certmanager.FrontProxyClient:
		return true
	default:
		return false
	}
}

func needsKarmadaAltNames(id certmanager.IdentityID) bool {
	switch id {
	case certmanager.AggregatedAPIServerServer, certmanager.WebhookServer:
		return true
	default:
		return false
	}
}
