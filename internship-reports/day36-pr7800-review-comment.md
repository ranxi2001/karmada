Target: https://github.com/karmada-io/karmada/pull/7800

Line: `pkg/detector/waiting_store.go:106` at head `dc1b9c4a8aa55100e6b35dfda4cefff82725e469`

Status: draft only; not posted

Could we also quantify the retained-heap side of this trade-off at the PR's scale? In a review-only test with 24,564 objects (same GVK/namespace, unique names, one label), the old key map retained about 3.15 MB while this store retained about 40.56 MB. With nil labels it still retained about 32.30 MB; clearing only `byGVKName` before GC reduced that to about 9.64 MB, so its per-name singleton sets dominate this distribution. The exact namespace+name benchmark reads `objects` directly and does not use this index. Cross-namespace name selectors still need efficient lookup, so the trade-off may be worthwhile, but the current query `alloc_space` profiles do not show this persistent peak. Could we add same-scale `inuse_space`/retained-heap evidence and either document the expected bound or use a denser/lazier name index?
