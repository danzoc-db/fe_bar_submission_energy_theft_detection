"""Acceptance tests — AI Governance page."""


class TestPIIMatrix:
    """TC-G1: PII field classification matrix."""

    def test_pii_matrix_returns_200(self, client):
        """MUST: PII matrix endpoint responds."""
        r = client.get("/api/governance/pii-matrix")
        assert r.status_code == 200

    def test_pii_matrix_is_non_empty(self, client):
        """MUST: Matrix contains at least one entry."""
        data = client.get("/api/governance/pii-matrix").json()
        assert len(data) > 0

    def test_pii_matrix_has_required_fields(self, client):
        """MUST: Each entry has table, field, tag, and regulatory basis."""
        data = client.get("/api/governance/pii-matrix").json()
        for entry in data:
            assert "table_name" in entry
            assert "field_name" in entry
            assert "pii_tag" in entry
            assert "regulatory_basis" in entry

    def test_pii_matrix_covers_key_tables(self, client):
        """MUST: Matrix covers smart_meter_reads, meters, and anomaly_scores."""
        data = client.get("/api/governance/pii-matrix").json()
        tables = {entry["table_name"] for entry in data}
        assert "smart_meter_reads" in tables
        assert "meters" in tables
        assert "anomaly_scores" in tables


class TestColumnMetadata:
    """TC-G1b: Column metadata from UC INFORMATION_SCHEMA."""

    def test_column_metadata_returns_200(self, client):
        """MUST: Column metadata endpoint responds."""
        r = client.get("/api/governance/column-metadata")
        assert r.status_code == 200

    def test_column_metadata_is_list(self, client):
        """MUST: Returns a list (empty without SQL connection)."""
        data = client.get("/api/governance/column-metadata").json()
        assert isinstance(data, list)

    def test_column_metadata_fields_when_present(self, client):
        """SHOULD: If data returned, each entry has required fields."""
        data = client.get("/api/governance/column-metadata").json()
        for entry in data:
            assert "table_name" in entry
            assert "column_name" in entry


class TestAIComponents:
    """TC-G2: AI component registry."""

    def test_components_returns_200(self, client):
        """MUST: Component registry endpoint responds."""
        r = client.get("/api/governance/components")
        assert r.status_code == 200

    def test_components_has_five_entries(self, client):
        """MUST: Registry contains 5 AI components (2 ML + 2 LLM + 1 Genie)."""
        data = client.get("/api/governance/components").json()
        assert len(data) == 5

    def test_components_cover_all_types(self, client):
        """MUST: Registry covers ML Model, LLM, and Genie Space."""
        data = client.get("/api/governance/components").json()
        types = {item["component_type"] for item in data}
        assert any("ML Model" in t for t in types)
        assert any("LLM" in t for t in types)
        assert any("Genie" in t for t in types)

    def test_components_have_pii_fields(self, client):
        """MUST: Each component lists its PII fields accessed."""
        data = client.get("/api/governance/components").json()
        for item in data:
            assert "pii_fields_accessed" in item
            assert isinstance(item["pii_fields_accessed"], list)
            assert len(item["pii_fields_accessed"]) > 0


class TestAIGatewayAudit:
    """TC-G3: AI Gateway audit trail."""

    def test_audit_returns_200(self, client):
        """MUST: Audit endpoint responds."""
        r = client.get("/api/governance/audit")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestModelPerformance:
    """TC-G4: Model performance metrics."""

    def test_model_performance_returns_200(self, client):
        """SHOULD: Model performance endpoint responds."""
        r = client.get("/api/governance/model-performance")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestExternalLineage:
    """TC-G5: External Power BI lineage endpoint.

    Without a metastore connection (no SQL_WAREHOUSE_ID, no privileges) the
    endpoint must still return a well-formed response with source='fallback'
    so the UI toggle keeps working in dev / unit-test mode.
    """

    def test_external_lineage_returns_200(self, client):
        r = client.get("/api/governance/external-lineage")
        assert r.status_code == 200

    def test_external_lineage_shape(self, client):
        data = client.get("/api/governance/external-lineage").json()
        assert "nodes" in data
        assert "edges" in data
        assert "source" in data
        assert data["source"] in ("live", "fallback")

    def test_external_lineage_has_four_reports(self, client):
        data = client.get("/api/governance/external-lineage").json()
        assert len(data["nodes"]) == 4
        names = {n["name"] for n in data["nodes"]}
        assert names == {
            "pbi_revenue_protection_exec",
            "pbi_field_ops_heatmap",
            "pbi_customer_insights",
            "pbi_regulatory_compliance",
        }

    def test_external_lineage_has_at_least_ten_edges(self, client):
        data = client.get("/api/governance/external-lineage").json()
        assert len(data["edges"]) >= 10

    def test_external_lineage_edge_shape(self, client):
        data = client.get("/api/governance/external-lineage").json()
        for e in data["edges"]:
            assert "source_table" in e
            assert "source_column" in e
            assert "target_external" in e
            assert "target_column" in e

    def test_external_lineage_targets_match_nodes(self, client):
        """Every edge must target one of the registered external nodes."""
        data = client.get("/api/governance/external-lineage").json()
        node_names = {n["name"] for n in data["nodes"]}
        for e in data["edges"]:
            assert e["target_external"] in node_names, (
                f"edge targets unknown external object: {e['target_external']}"
            )

    def test_external_lineage_node_columns_cover_edge_targets(self, client):
        """Every edge target_column should be in the corresponding node's columns."""
        data = client.get("/api/governance/external-lineage").json()
        cols_by_name = {n["name"]: set(n["columns"]) for n in data["nodes"]}
        for e in data["edges"]:
            assert e["target_column"] in cols_by_name[e["target_external"]], (
                f"edge target column {e['target_column']} not declared on "
                f"node {e['target_external']}"
            )


