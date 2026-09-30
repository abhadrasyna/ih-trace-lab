"""Quick TR-1 probe for dedicated vs shared Lightstep tenant resolution."""

import json


TENANTS = {
    "iye9omdf": {
        "opco": "South Africa",
        "project": "mcs-go-prod-iye9omdf-eu",
        "region": "EU",
        "shared_project": False,
    },
    "apbyfj9d": {
        "opco": "Ghana",
        "project": "mcs-go-prod-mtn-1-eu",
        "region": "EU",
        "shared_project": True,
    },
}


def resolve_lightstep_context(go_id):
    tenant = TENANTS[go_id]
    filter_value = None
    if tenant["shared_project"]:
        filter_value = {"sessionInfo.busUnitId": go_id}
    return {
        "project": tenant["project"],
        "region": tenant["region"],
        "filter": filter_value,
    }


def main():
    for go_id in ("iye9omdf", "apbyfj9d"):
        resolved = resolve_lightstep_context(go_id)
        print(json.dumps({"go_id": go_id, "resolved": resolved}, sort_keys=True))


if __name__ == "__main__":
    main()
