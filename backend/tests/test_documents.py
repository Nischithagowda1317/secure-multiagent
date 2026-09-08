from __future__ import annotations

from conftest import login_headers


ADMIN = "abd.alruhmin.alnasar@nexacore.example"


def test_temporary_txt_attachment_is_analyzed(client):
    headers = login_headers(client, ADMIN)
    content = (
        b"Vendor onboarding rule: all critical suppliers require a security review "
        b"and Finance Manager approval before activation."
    )
    response = client.post(
        "/api/chat",
        headers=headers,
        data={"message": "What approval is required for critical supplier onboarding?"},
        files={"files": ("vendor_note.txt", content, "text/plain")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "security review" in payload["answer"].lower()
    assert any(source["source_type"] == "Temporary upload" for source in payload["sources"])
