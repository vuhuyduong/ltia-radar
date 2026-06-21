"""
citation_filter — Utility to filter out outlier citation sources.
Groups citations into time-based clusters and removes minority clusters that are far from the primary article.
"""

from datetime import datetime
from typing import Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def filter_outlier_citations(
    citations: List[Any],
    ref_time: Optional[datetime] = None,
    primary_source_url: Optional[str] = None,
    threshold_days: float = 7.0,
    cluster_gap_days: float = 5.0,
    max_minority_ratio: float = 0.35,
    max_minority_count: int = 3,
) -> List[Any]:
    """
    Filters out citations that are outliers in terms of publish time.
    
    Uses single-linkage time clustering to partition citations. Any cluster that does not
    contain the primary citation is discarded if it is 'far' from the reference time
    and represents a 'minority' cluster.
    
    Args:
        citations: List of dicts or ArticleCitation objects.
        ref_time: The reference datetime (usually primary article publish time).
        primary_source_url: The URL of the primary article.
        threshold_days: Time distance threshold in days to flag a cluster as far.
        cluster_gap_days: Gap in days to separate clusters.
        max_minority_ratio: Max percentage (ratio) of citations in a cluster to be considered a minority.
        max_minority_count: Max absolute count of citations in a cluster to be considered a minority.
        
    Returns:
        Filtered list of citations (same types as input) preserving their original order.
    """
    if not citations:
        return citations

    def get_val(item: Any, key: str) -> Any:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    def get_datetime(val: Any) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                try:
                    from dateutil import parser
                    return parser.parse(val)
                except Exception:
                    return None
        return None

    # 1. Identify primary citation
    primary_cite = None
    if primary_source_url:
        for c in citations:
            if get_val(c, "source_url") == primary_source_url:
                primary_cite = c
                break
    if primary_cite is None:
        primary_cite = citations[0]

    # Find original index of the primary citation
    primary_idx = 0
    for i, c in enumerate(citations):
        if c is primary_cite:
            primary_idx = i
            break

    # 2. Resolve reference time (ref_time)
    if ref_time is None:
        ref_time = get_datetime(get_val(primary_cite, "publish_time"))
    if ref_time is None:
        # Fallback to first citation with a publish time
        for c in citations:
            pt = get_datetime(get_val(c, "publish_time"))
            if pt is not None:
                ref_time = pt
                break
    if ref_time is None:
        # No time info available across any citation; cannot filter
        return citations

    ref_time_naive = ref_time.replace(tzinfo=None) if ref_time.tzinfo is not None else ref_time

    # 3. Associate each citation with its naive publish time (fallback to ref_time_naive if None)
    citations_with_time = []
    for idx, c in enumerate(citations):
        pt = get_datetime(get_val(c, "publish_time"))
        if pt is not None:
            pt_naive = pt.replace(tzinfo=None) if pt.tzinfo is not None else pt
        else:
            pt_naive = ref_time_naive
        citations_with_time.append((idx, c, pt_naive))

    # 4. Sort and cluster citations using a time-gap threshold
    sorted_citations = sorted(citations_with_time, key=lambda x: x[2])
    clusters = []
    current_cluster = []

    for idx, c, pt_naive in sorted_citations:
        if not current_cluster:
            current_cluster.append((idx, c, pt_naive))
        else:
            prev_pt_naive = current_cluster[-1][2]
            gap = (pt_naive - prev_pt_naive).total_seconds() / 86400.0
            if gap <= cluster_gap_days:
                current_cluster.append((idx, c, pt_naive))
            else:
                clusters.append(current_cluster)
                current_cluster = [(idx, c, pt_naive)]
    if current_cluster:
        clusters.append(current_cluster)

    # 5. Identify primary cluster
    primary_cluster_idx = -1
    for i, cluster in enumerate(clusters):
        if any(item[0] == primary_idx for item in cluster):
            primary_cluster_idx = i
            break

    def get_median_time(cluster_list: List[tuple]) -> datetime:
        times = sorted([item[2] for item in cluster_list])
        n = len(times)
        if n % 2 == 1:
            return times[n // 2]
        else:
            t1 = times[n // 2 - 1]
            t2 = times[n // 2]
            return t1 + (t2 - t1) / 2

    # 6. Apply filtering logic to clusters
    keep_indices = set()
    keep_indices.add(primary_idx)  # Safety first: always keep the primary citation

    if primary_cluster_idx != -1:
        for idx, _, _ in clusters[primary_cluster_idx]:
            keep_indices.add(idx)

    total_citations = len(citations)

    for i, cluster in enumerate(clusters):
        if i == primary_cluster_idx:
            continue

        median_time = get_median_time(cluster)
        diff_days = abs((median_time - ref_time_naive).total_seconds()) / 86400.0

        is_far = diff_days > threshold_days
        is_minority = (len(cluster) <= max_minority_count) or (len(cluster) / total_citations <= max_minority_ratio)

        if is_far and is_minority:
            logger.info(
                f"Filtering out citation cluster of size {len(cluster)}: "
                f"median time {median_time} is {diff_days:.1f} days away from ref_time {ref_time_naive}"
            )
            for _, c, _ in cluster:
                logger.info(f"Filtered out: {get_val(c, 'title')} ({get_val(c, 'source_url')})")
        else:
            for idx, _, _ in cluster:
                keep_indices.add(idx)

    # Return filtered citations in original order
    return [citations[i] for i in range(total_citations) if i in keep_indices]
