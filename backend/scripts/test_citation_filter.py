import sys
from datetime import datetime, timedelta

# Ensure backend directory is in path
sys.path.append(".")

from app.domain.utils.citation_filter import filter_outlier_citations


def run_tests():
    print("Running citation filter tests...")
    ref_time = datetime(2026, 6, 20, 12, 0, 0)

    # Test Case 1: All close in time
    citations = [
        {"title": "Main News", "source_url": "url1", "publish_time": ref_time},
        {"title": "Similar News A", "source_url": "url2", "publish_time": ref_time - timedelta(hours=12)},
        {"title": "Similar News B", "source_url": "url3", "publish_time": ref_time + timedelta(days=1)},
    ]
    res = filter_outlier_citations(citations, ref_time=ref_time, primary_source_url="url1")
    assert len(res) == 3, f"Expected 3, got {len(res)}"
    print("Test Case 1 passed!")

    # Test Case 2: One outlier, far in time, size 1 (minority)
    citations = [
        {"title": "Main News", "source_url": "url1", "publish_time": ref_time},
        {"title": "Similar News A", "source_url": "url2", "publish_time": ref_time - timedelta(hours=12)},
        {"title": "Outlier from 35 days ago", "source_url": "url3", "publish_time": ref_time - timedelta(days=35)},
    ]
    res = filter_outlier_citations(citations, ref_time=ref_time, primary_source_url="url1")
    assert len(res) == 2, f"Expected 2, got {len(res)}"
    assert res[0]["source_url"] == "url1"
    assert res[1]["source_url"] == "url2"
    print("Test Case 2 passed!")

    # Test Case 3: A group of outliers that is NOT a minority (majority in size)
    # 4 outliers, 2 recent. Size 4 > 3, ratio 4/6 = 66% > 35%. Should be kept.
    citations = [
        {"title": "Main News", "source_url": "url1", "publish_time": ref_time},
        {"title": "Similar News A", "source_url": "url2", "publish_time": ref_time - timedelta(hours=12)},
        {"title": "Far A", "source_url": "url3", "publish_time": ref_time - timedelta(days=30)},
        {"title": "Far B", "source_url": "url4", "publish_time": ref_time - timedelta(days=30)},
        {"title": "Far C", "source_url": "url5", "publish_time": ref_time - timedelta(days=30, hours=2)},
        {"title": "Far D", "source_url": "url6", "publish_time": ref_time - timedelta(days=30, hours=5)},
    ]
    res = filter_outlier_citations(citations, ref_time=ref_time, primary_source_url="url1")
    assert len(res) == 6, f"Expected 6, got {len(res)}"
    print("Test Case 3 passed!")

    # Test Case 4: A group of outliers that IS a minority (size 2 <= 3)
    citations = [
        {"title": "Main News", "source_url": "url1", "publish_time": ref_time},
        {"title": "Similar News A", "source_url": "url2", "publish_time": ref_time - timedelta(hours=12)},
        {"title": "Far A", "source_url": "url3", "publish_time": ref_time - timedelta(days=30)},
        {"title": "Far B", "source_url": "url4", "publish_time": ref_time - timedelta(days=30, hours=1)},
    ]
    res = filter_outlier_citations(citations, ref_time=ref_time, primary_source_url="url1")
    assert len(res) == 2, f"Expected 2, got {len(res)}"
    assert res[0]["source_url"] == "url1"
    assert res[1]["source_url"] == "url2"
    print("Test Case 4 passed!")

    # Test Case 5: Missing publish_time (should be kept)
    citations = [
        {"title": "Main News", "source_url": "url1", "publish_time": ref_time},
        {"title": "No Time News", "source_url": "url2", "publish_time": None},
    ]
    res = filter_outlier_citations(citations, ref_time=ref_time, primary_source_url="url1")
    assert len(res) == 2, f"Expected 2, got {len(res)}"
    print("Test Case 5 passed!")

    print("All tests passed successfully!")


if __name__ == "__main__":
    run_tests()
