package luavm

import (
	"encoding/json"
	"strings"
	"testing"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"

	workv1alpha2 "github.com/karmada-io/karmada/pkg/apis/work/v1alpha2"
	"github.com/karmada-io/karmada/pkg/util/helper"
)

func TestIssue7643QuantityConversionEvidence(t *testing.T) {
	q := resource.MustParse("100m")
	t.Logf("resource.MustParse(%q): String=%q AsApproximateFloat64=%v Value=%d MilliValue=%d", "100m", q.String(), q.AsApproximateFloat64(), q.Value(), q.MilliValue())

	var fromNumber resource.Quantity
	if err := json.Unmarshal([]byte(`0.1`), &fromNumber); err != nil {
		t.Fatalf("unmarshal numeric quantity: %v", err)
	}
	t.Logf("json.Unmarshal(0.1): String=%q AsApproximateFloat64=%v Value=%d MilliValue=%d Equal100m=%v", fromNumber.String(), fromNumber.AsApproximateFloat64(), fromNumber.Value(), fromNumber.MilliValue(), fromNumber.Equal(q))
	if !fromNumber.Equal(q) {
		t.Fatalf("json.Unmarshal(0.1) = %q, want quantity equal to 100m", fromNumber.String())
	}

	var fromOne resource.Quantity
	if err := json.Unmarshal([]byte(`1`), &fromOne); err != nil {
		t.Fatalf("unmarshal numeric quantity: %v", err)
	}
	t.Logf("json.Unmarshal(1): String=%q AsApproximateFloat64=%v Value=%d MilliValue=%d Equal100m=%v", fromOne.String(), fromOne.AsApproximateFloat64(), fromOne.Value(), fromOne.MilliValue(), fromOne.Equal(q))
	if fromOne.Equal(q) {
		t.Fatalf("json.Unmarshal(1) unexpectedly equals 100m")
	}
}

func TestIssue7643LuaComponentMemoryEvidence(t *testing.T) {
	vm := New(true, 1)
	obj := &unstructured.Unstructured{Object: map[string]any{
		"spec": map[string]any{},
	}}
	script := `
function GetComponents(obj)
    local kube = require("kube")
    return {
        {
            name = "jobmanager",
            replicas = 1,
            replicaRequirements = {
                resourceRequest = {
                    cpu = "150m",
                    memory = kube.getResourceQuantity("100m"),
                },
            },
        },
    }
end
`
	components, err := vm.GetComponents(obj, script)
	if err != nil {
		t.Fatalf("GetComponents() error: %v", err)
	}
	raw, err := json.Marshal(components)
	if err != nil {
		t.Fatalf("marshal components: %v", err)
	}
	t.Logf("components JSON after Lua conversion: %s", string(raw))
	if !strings.Contains(string(raw), `"memory":"100m"`) {
		t.Fatalf("components JSON should keep memory as 100m, got %s", string(raw))
	}
	got := components[0].ReplicaRequirements.ResourceRequest[corev1.ResourceMemory]
	want := resource.MustParse("100m")
	t.Logf("component memory quantity: String=%q AsApproximateFloat64=%v Value=%d MilliValue=%d Equal100m=%v", got.String(), got.AsApproximateFloat64(), got.Value(), got.MilliValue(), got.Equal(want))
	if !got.Equal(want) {
		t.Fatalf("component memory = %q, want quantity equal to 100m", got.String())
	}

	usage := resource.Quantity{}
	for _, component := range components {
		q := component.ReplicaRequirements.ResourceRequest[corev1.ResourceMemory]
		q.Mul(int64(component.Replicas))
		usage.Add(q)
	}
	t.Logf("manual aggregate for one component: String=%q Value=%d MilliValue=%d", usage.String(), usage.Value(), usage.MilliValue())
}

func TestIssue7643ResourceUsageEvidence(t *testing.T) {
	rb := &workv1alpha2.ResourceBinding{
		Spec: workv1alpha2.ResourceBindingSpec{
			Clusters: []workv1alpha2.TargetCluster{{Name: "member1", Replicas: 1}},
			Components: []workv1alpha2.Component{
				{
					Name:     "jobmanager",
					Replicas: 1,
					ReplicaRequirements: &workv1alpha2.ComponentReplicaRequirements{
						ResourceRequest: corev1.ResourceList{
							corev1.ResourceCPU:    resource.MustParse("150m"),
							corev1.ResourceMemory: resource.MustParse("100m"),
						},
					},
				},
				{
					Name:     "taskmanager",
					Replicas: 1,
					ReplicaRequirements: &workv1alpha2.ComponentReplicaRequirements{
						ResourceRequest: corev1.ResourceList{
							corev1.ResourceCPU:    resource.MustParse("150m"),
							corev1.ResourceMemory: resource.MustParse("100m"),
						},
					},
				},
			},
		},
	}
	usage := helper.CalculateResourceUsage(rb)
	raw, err := json.Marshal(usage)
	if err != nil {
		t.Fatalf("marshal usage: %v", err)
	}
	t.Logf("CalculateResourceUsage JSON: %s", string(raw))
	if !strings.Contains(string(raw), `"memory":"200m"`) {
		t.Fatalf("usage JSON should aggregate memory as 200m, got %s", string(raw))
	}
	memory := usage[corev1.ResourceMemory]
	t.Logf("memory usage: String=%q Value=%d MilliValue=%d Equal200m=%v", memory.String(), memory.Value(), memory.MilliValue(), memory.Equal(resource.MustParse("200m")))
	if !memory.Equal(resource.MustParse("200m")) {
		t.Fatalf("memory usage = %q, want quantity equal to 200m", memory.String())
	}
}

func TestIssue7643ComponentJSONOneByteEvidence(t *testing.T) {
	components := []workv1alpha2.Component{{
		Name:     "jobmanager",
		Replicas: 1,
		ReplicaRequirements: &workv1alpha2.ComponentReplicaRequirements{
			ResourceRequest: corev1.ResourceList{
				corev1.ResourceMemory: resource.MustParse("1"),
			},
		},
	}}
	raw, err := json.Marshal(components)
	if err != nil {
		t.Fatalf("marshal components: %v", err)
	}
	t.Logf("component JSON with literal 1-byte memory: %s", string(raw))
	if !strings.Contains(string(raw), `"memory":"1"`) {
		t.Fatalf("literal 1-byte memory should marshal as 1, got %s", string(raw))
	}
}
