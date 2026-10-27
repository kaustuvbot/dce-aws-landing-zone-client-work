"""Offline checks for this fixed POC, not a validator for a merged LZA deployment.

Usage: python3 poc-config/validate_fragments.py /path/to/landing-zone-accelerator-on-aws
Requires PyYAML and jsonschema; use the release/v1.16.3 source checkout.

What it does:
  1. Parses every *.fragment.yaml, rejecting duplicate YAML keys.
  2. Validates each supplied subtree against the pinned LZA JSON schema. Because
     these are MERGE fragments, the required top-level keys of a whole config file
     are intentionally absent; only the supplied sub-objects are validated.
  3. Runs POC-specific reference checks (account names, OU names, CIDRs, AZs,
     routes, attachments, RAM share, SCP JSON).
"""

import ipaddress
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

# file name -> (schema file, root definition, {root key: definition name})
FRAGMENTS = {
    "01-organization.fragment.yaml": (
        "organization-config.json", "IOrganizationConfig", {}),
    "02-accounts.fragment.yaml": (
        "accounts-config.json", "IAccountsConfig", {}),
    "03-network.fragment.yaml": (
        "network-config.json", "INetworkConfig", {}),
    "04-security.fragment.yaml": (
        "security-config.json", "ISecurityConfig",
        {"centralSecurityServices": "ICentralSecurityServicesConfig"}),
    "05-global-tags.fragment.yaml": (
        "global-config.json", "IGlobalConfig", {}),
    "06-controls-organization.fragment.yaml": (
        "organization-config.json", "IOrganizationConfig", {}),
    "07-controls-security.fragment.yaml": (
        "security-config.json", "ISecurityConfig",
        {"awsConfig": "IAwsConfig"}),
}


def validator_for(schema, definition):
    part = dict(schema["definitions"][definition])
    part["definitions"] = schema["definitions"]
    return Draft7Validator(part)


def validate_instance(schema, property_schema, instance):
    """Validate an instance against a schema fragment, resolving local $refs."""
    part = dict(property_schema)
    part["definitions"] = schema["definitions"]
    Draft7Validator(part).validate(instance)


def load_fragments(here):
    fragments = {}
    for name in FRAGMENTS:
        path = here / name
        if not path.exists():
            raise AssertionError(f"Missing fragment file: {name}")
        fragments[name] = yaml.load(path.read_text(), Loader=UniqueLoader)
    return fragments


def validate(source):
    schemas = source / "source/packages/@aws-accelerator/config/lib/schemas"
    here = Path(__file__).resolve().parent
    fragments = load_fragments(here)

    for name, (schema_file, root_def, sub_defs) in FRAGMENTS.items():
        schema = json.loads((schemas / schema_file).read_text())
        data = fragments[name]
        root_props = schema["definitions"][root_def]["properties"]
        for key, value in data.items():
            assert key in root_props, f"{name}: unknown root key {key}"
            if key in sub_defs:
                # Validate each supplied child of a partially supplied object.
                child_schema = schema["definitions"][sub_defs[key]]["properties"]
                for child, child_value in value.items():
                    assert child in child_schema, f"{name}: unknown {key}.{child}"
                    validate_instance(schema, child_schema[child], child_value)
            else:
                # Validate the supplied value against the root property schema.
                validate_instance(schema, root_props[key], value)
        print(f"Schema subtree PASS: {name}")

    accounts = fragments["02-accounts.fragment.yaml"]["workloadAccounts"]
    account_names = {a["name"] for a in accounts}
    assert account_names == {"Network", "NonProduction"}, account_names
    ous = {o["name"] for o in fragments["01-organization.fragment.yaml"]["organizationalUnits"]}
    assert all(a["organizationalUnit"] in ous and a["warm"] is False for a in accounts)
    assert all("@example.invalid" in a["email"] for a in accounts), \
        "placeholder e-mails must be replaced in AWS before committing"

    network = fragments["03-network.fragment.yaml"]
    assert set(network) == {"transitGateways", "vpcs"}
    tgw, = network["transitGateways"]
    assert tgw["account"] == "Network"
    assert tgw["region"] == "eu-west-2"
    assert tgw["shareTargets"] == {"accounts": ["NonProduction"]}
    assert tgw["autoAcceptSharingAttachments"] == "enable"
    table, = tgw["routeTables"]
    assert table["routes"] == []

    vpcs = {v["name"]: v for v in network["vpcs"]}
    assert set(vpcs) == {"DCE-POC-VPC", "DCE-POC-SOURCE-VPC"}, set(vpcs)
    dest, source = vpcs["DCE-POC-VPC"], vpcs["DCE-POC-SOURCE-VPC"]
    assert dest["account"] == "NonProduction"
    assert source["account"] == "Network"

    for vpc in (dest, source):
        assert vpc["region"] == "eu-west-2"
        assert vpc["internetGateway"] is False
        assert not any(vpc.get(k) for k in ("natGateways", "interfaceEndpoints", "gatewayEndpoints"))
        cidr = ipaddress.ip_network(vpc["cidrs"][0])
        subnets = {s["name"]: s for s in vpc["subnets"]}
        assert len(subnets) == len(vpc["subnets"]) == 4
        networks = [ipaddress.ip_network(s["ipv4CidrBlock"]) for s in subnets.values()]
        assert all(n.subnet_of(cidr) for n in networks)
        assert all(not a.overlaps(b) for i, a in enumerate(networks) for b in networks[i + 1:])
        tables = {r["name"]: r for r in vpc["routeTables"]}
        assert len(tables) == len(vpc["routeTables"]) == 4
        assert all(s["routeTable"] in tables for s in subnets.values())
        assert all(s["availabilityZone"] in ("a", "b") for s in subnets.values())
        assert {s["availabilityZone"] for s in subnets.values()} == {"a", "b"}
        attachment, = vpc["transitGatewayAttachments"]
        assert attachment["transitGateway"] == {"name": tgw["name"], "account": tgw["account"]}
        assert set(attachment["subnets"]) <= set(subnets)
        assert {subnets[n]["availabilityZone"] for n in attachment["subnets"]} == {"a", "b"}
        assert attachment["routeTableAssociations"] == attachment["routeTablePropagations"] == [table["name"]]

    # Cross-VPC routes: each application route table points at the peer /16 via the TGW.
    for vpc, peer_cidr in ((dest, "10.10.0.0/16"), (source, "10.20.0.0/16")):
        app_tables = [r for r in vpc["routeTables"] if r["name"].endswith("APP-A") or r["name"].endswith("APP-B")]
        assert len(app_tables) == 2
        for rt in app_tables:
            routes = [r for r in rt["routes"] if r["destination"] == peer_cidr]
            assert len(routes) == 1, (vpc["name"], rt["name"], rt["routes"])
            assert routes[0]["type"] == "transitGateway"
            assert routes[0]["target"] == tgw["name"]
        tgw_tables = [r for r in vpc["routeTables"] if r["name"].endswith("TGW-A") or r["name"].endswith("TGW-B")]
        assert all(r["routes"] == [] for r in tgw_tables)

    # The RAM share target must be the account that does NOT own the TGW.
    assert dest["account"] in tgw["shareTargets"]["accounts"]
    assert source["account"] not in tgw["shareTargets"]["accounts"]

    central = fragments["04-security.fragment.yaml"]["centralSecurityServices"]
    assert central["delegatedAdminAccount"] == "Audit"
    for service in ("guardduty", "securityHub"):
        assert central[service]["enable"] is True
        assert central[service]["excludeRegions"] == ["us-east-1"]
    assert central["securityHub"]["standards"][0]["name"].startswith("AWS Foundational Security Best Practices")

    tags = fragments["05-global-tags.fragment.yaml"]["tags"]
    assert len({t["key"] for t in tags}) == len(tags)
    assert all(isinstance(t["value"], str) for t in tags)

    scps = fragments["06-controls-organization.fragment.yaml"]["serviceControlPolicies"]
    scp, = scps
    assert scp["type"] == "customerManaged"
    assert scp["strategy"] == "deny-list"
    assert scp["deploymentTargets"]["organizationalUnits"] == ["Non-Production"]
    policy_path = here / scp["policy"]
    assert policy_path.exists(), f"SCP JSON not found: {scp['policy']}"
    policy = json.loads(policy_path.read_text())
    statement, = policy["Statement"]
    assert statement["Effect"] == "Deny"
    assert statement["Action"] == "iam:CreateUser"

    rule_sets = fragments["07-controls-security.fragment.yaml"]["awsConfig"]["ruleSets"]
    rule_set, = rule_sets
    assert rule_set["deploymentTargets"]["accounts"] == ["NonProduction"]
    rule, = rule_set["rules"]
    assert rule["identifier"] == "REQUIRED_TAGS"
    assert rule["inputParameters"] == {"tag1Key": "Project"}
    assert rule["complianceResourceTypes"] == ["AWS::EC2::Instance"]

    print("POC reference/CIDR/AZ/scope checks PASS. Placeholders remain intentionally.")
    print("NOT checked: generated baseline, AWS state, full LZA semantic validation or deployment.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    validate(Path(sys.argv[1]))
