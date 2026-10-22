import hashlib 
import math
import re
from collections import defaultdict


GROUPING_RADIUS_METERS = 300


def normalize_street_name(street_name):
    """Normalize street names for consistent comparisons."""
    if not street_name:
        return ""

    return re.sub(r"\s+", " ", street_name).strip().casefold()


def distance_in_meters(report_a, report_b):
    """Calculate the distance between two report coordinates."""
    earth_radius = 6_371_000

    lat1 = math.radians(report_a.latitude)
    lat2 = math.radians(report_b.latitude)

    lat_difference = math.radians(
        report_b.latitude - report_a.latitude
    )
    lon_difference = math.radians(
        report_b.longitude - report_a.longitude
    )

    a = (
        math.sin(lat_difference / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(lon_difference / 2) ** 2
    )

    # Protect against floating-point rounding errors.
    a = min(1.0, max(0.0, a))

    return 2 * earth_radius * math.asin(math.sqrt(a))


def group_reports_by_area(
    reports,
    radius_meters=GROUPING_RADIUS_METERS,
):
    """
    Group reports by normalized street name and proximity.

    Reports on the same street can belong to the same cluster
    when they are connected by distances within the radius.
    Reports without a street name are kept in separate groups
    rather than incorrectly combining unrelated locations.
    """
    reports_by_street = defaultdict(list)

    for report in reports:
        street_key = normalize_street_name(report.street_name)

        if street_key:
            reports_by_street[street_key].append(report)

    area_groups = []

    for street_key, street_reports in reports_by_street.items():
        # Each report initially belongs to its own cluster.
        parent = list(range(len(street_reports)))

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]

            return index

        def union(index_a, index_b):
            root_a = find(index_a)
            root_b = find(index_b)

            if root_a != root_b:
                parent[root_b] = root_a

        # Connect nearby reports on the same street.
        for i in range(len(street_reports)):
            for j in range(i + 1, len(street_reports)):
                if (
                    distance_in_meters(
                        street_reports[i],
                        street_reports[j],
                    )
                    <= radius_meters
                ):
                    union(i, j)

        # Collect connected reports into clusters.
        clusters = defaultdict(list)

        for index, report in enumerate(street_reports):
            clusters[find(index)].append(report)

        for cluster_reports in clusters.values():
            area_groups.append(
                build_area_summary(
                    street_key,
                    cluster_reports,
                )
            )

    # Reports without a street name cannot be safely matched
    # to a street-based group.
    for report in reports:
        if not normalize_street_name(report.street_name):
            area_groups.append(
                build_area_summary(
                    "",
                    [report],
                )
            )

    # Show the areas with the most reports first.
    area_groups.sort(
        key=lambda group: (
            group["unresolved_count"],
            group["total_reports"],
        ),
        reverse=True,
    )

    return area_groups


def build_area_summary(street_key, reports):
    """Calculate impact counts for one area cluster."""

    unresolved_reports = [
        report for report in reports
        if report.status != "Repaired"
    ]

    severity_counts = {
        "High": sum(
            report.severity == "High" for report in reports 
        ),
        "Medium": sum(
            report.severity == "Medium" for report in reports 
        ),
        "Low": sum(
            report.severity == "Low" for report in reports 
        ),
    }

    # Count high-severity reports that still need attention.
    unresolved_high_count = sum(
        report.severity == "High"
        for report in unresolved_reports 
    )

    unresolved_count = len(unresolved_reports)

    # Count unresolved reports by severity
    unresolved_medium_count = sum(
        report.severity == "Medium"
        for report in unresolved_reports
    )

    unresolved_low_count = sum(
        report.severity == "Low"
        for report in unresolved_reports
    )

    # Determine the area's repair priority.
    if unresolved_count == 0:
        priority = "Resolved"
        priority_level = "resolved"

    elif unresolved_high_count > 0:
        priority = "High Priority"
        priority_level = "high"

    elif unresolved_medium_count > 0:
        priority = "Medium Priority"
        priority_level = "medium"

    else:
        priority = "Routine Monitoring"
        priority_level = "low"

    center_latitude = sum(
        report.latitude for report in reports 
    ) / len(reports)

    center_longitude = sum(
        report.longitude for report in reports
    ) / len(reports) 

    display_street = next(
        (
            report.street_name.strip()
            for report in reports
            if report.street_name
            and report.street_name.strip()
        ),
        "Street name unavailable",
    )

    report_ids = sorted(report.id for report in reports)

    area_id = hashlib.sha256(
        ",".join(map(str, report_ids)).encode('utf-8')
    ).hexdigest()[:16]

    return {
        "area_id": area_id,
        "street_name": display_street,
        "street_key": street_key,
        "reports": sorted(
            reports,
            key=lambda report: report.created_at,
            reverse=True,
        ),
        "total_reports": len(reports),
        "unresolved_count": unresolved_count,
        "repaired_count": len(reports) - unresolved_count,
        "severity_counts": severity_counts,
        "unresolved_high_count": unresolved_high_count,
        "latitude": center_latitude,
        "longitude": center_longitude,
        "has_high_severity": unresolved_high_count > 0,
        "priority": priority,
        "priority_level": priority_level,
    }