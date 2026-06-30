package thirdparty

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/util/yaml"

	configv1alpha1 "github.com/karmada-io/karmada/pkg/apis/config/v1alpha1"
	workv1alpha2 "github.com/karmada-io/karmada/pkg/apis/work/v1alpha2"
	"github.com/karmada-io/karmada/pkg/util/helper"
)

func TestIssue7643FlinkDefaultCustomizationEvidence(t *testing.T) {
	data, err := os.ReadFile("resourcecustomizations/flink.apache.org/v1beta1/FlinkDeployment/customizations.yaml")
	if err != nil {
		t.Fatalf("read customization: %v", err)
	}
	config := &configv1alpha1.ResourceInterpreterCustomization{}
	if err := yaml.NewYAMLOrJSONDecoder(bytes.NewReader(data), 4096).Decode(config); err != nil {
		t.Fatalf("decode customization: %v", err)
	}

	ipt := NewConfigurableInterpreter()
	ipt.configManager.LoadConfig([]*configv1alpha1.ResourceInterpreterCustomization{config})

	obj := &unstructured.Unstructured{Object: map[string]any{
		"apiVersion": "flink.apache.org/v1beta1",
		"kind":       "FlinkDeployment",
		"metadata": map[string]any{
			"name":      "milli-memory-example",
			"namespace": "test-namespace",
		},
		"spec": map[string]any{
			"flinkConfiguration": map[string]any{
				"taskmanager.numberOfTaskSlots": "2",
			},
			"jobManager": map[string]any{
				"replicas": int64(1),
				"resource": map[string]any{
					"cpu":    "150m",
					"memory": "100m",
				},
			},
			"taskManager": map[string]any{
				"replicas": int64(1),
				"resource": map[string]any{
					"cpu":    "150m",
					"memory": "100m",
				},
			},
		},
	}}

	components, enabled, err := ipt.GetComponents(obj)
	if err != nil {
		t.Fatalf("GetComponents() error: %v", err)
	}
	if !enabled {
		t.Fatalf("GetComponents() not enabled")
	}
	raw, err := json.Marshal(components)
	if err != nil {
		t.Fatalf("marshal components: %v", err)
	}
	t.Logf("Flink components JSON: %s", string(raw))
	if !strings.Contains(string(raw), `"memory":"100m"`) {
		t.Fatalf("Flink components should keep memory as 100m, got %s", string(raw))
	}

	rb := &workv1alpha2.ResourceBinding{
		Spec: workv1alpha2.ResourceBindingSpec{
			Clusters:   []workv1alpha2.TargetCluster{{Name: "member1"}},
			Components: components,
		},
	}
	usage := helper.CalculateResourceUsage(rb)
	usageRaw, err := json.Marshal(usage)
	if err != nil {
		t.Fatalf("marshal usage: %v", err)
	}
	t.Logf("Flink CalculateResourceUsage JSON: %s", string(usageRaw))
	if !strings.Contains(string(usageRaw), `"memory":"200m"`) {
		t.Fatalf("Flink usage should aggregate memory as 200m, got %s", string(usageRaw))
	}

	for _, component := range components {
		memory := component.ReplicaRequirements.ResourceRequest[corev1.ResourceMemory]
		t.Logf("%s memory: String=%q Value=%d MilliValue=%d Equal100m=%v", component.Name, memory.String(), memory.Value(), memory.MilliValue(), memory.Equal(resource.MustParse("100m")))
		if !memory.Equal(resource.MustParse("100m")) {
			t.Fatalf("%s memory = %q, want quantity equal to 100m", component.Name, memory.String())
		}
	}
	memoryUsage := usage[corev1.ResourceMemory]
	t.Logf("total memory usage: String=%q Value=%d MilliValue=%d Equal200m=%v", memoryUsage.String(), memoryUsage.Value(), memoryUsage.MilliValue(), memoryUsage.Equal(resource.MustParse("200m")))
	if !memoryUsage.Equal(resource.MustParse("200m")) {
		t.Fatalf("total memory usage = %q, want quantity equal to 200m", memoryUsage.String())
	}
}
