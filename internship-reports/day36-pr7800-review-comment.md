Target: https://github.com/karmada-io/karmada/pull/7800

Line: `pkg/detector/waiting_store.go:106` at head `dc1b9c4a8aa55100e6b35dfda4cefff82725e469`

Status: posted on 2026-07-29 as [discussion_r3671589022](https://github.com/karmada-io/karmada/pull/7800#discussion_r3671589022); author replied in [discussion_r3679458690](https://github.com/karmada-io/karmada/pull/7800#discussion_r3679458690) and published the implementation/measurement follow-up in [issuecomment-5128747070](https://github.com/karmada-io/karmada/pull/7800#issuecomment-5128747070). Current-head local validation confirmed the hotspot reduction, and the [closure reply](https://github.com/karmada-io/karmada/pull/7800#discussion_r3681520974) was posted on 2026-07-30. GitHub rejected `resolveReviewThread` because `ranxi2001` lacks permission on this PR; no further finding is pending, and the author or a maintainer can resolve the thread.

The indexed-store approach looks good to me. It preserves the existing selector semantics while removing informer lookups and deep copies from the hot path, and the benchmark shows a substantial query improvement.

One non-blocking question is the retained-memory side of this trade-off. At the PR's 24,564-object scale, my review-only test measured about 3.15 MB for the old key map versus 40.56 MB for this store. With nil labels it still used 32.30 MB, and clearing only `byGVKName` reduced that to 9.64 MB, so the per-name singleton sets dominate this distribution. The exact namespace+name path reads `objects` directly, although cross-namespace name selectors still need efficient lookup.

This may still be the right trade-off. Could we add same-scale `inuse_space`/retained-heap evidence and either document the expected bound or consider a denser/lazier name index?
