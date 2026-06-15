"""Build a TAK Mission Data Package (.zip) for import into ATAK/WinTAK.

A data package is a zip containing the CoT file(s) plus MANIFEST/manifest.xml
describing them. Importing it drops the assessment marker (with the decision in
its remarks) straight onto the operator's TAK map.
"""

from __future__ import annotations

import io
import zipfile

_MANIFEST = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<MissionPackageManifest version="2">
  <Configuration>
    <Parameter name="uid" value="{uid}"/>
    <Parameter name="name" value="{name}"/>
    <Parameter name="onReceiveDelete" value="false"/>
  </Configuration>
  <Contents>
    <Content ignore="false" zipEntry="{entry}"/>
  </Contents>
</MissionPackageManifest>
"""


def build_package(cot_xml: str, uid: str, name: str = "CUAS Assessment", entry: str = "assessment.cot") -> bytes:
    """Return the bytes of a TAK data package zip containing one CoT marker."""
    manifest = _MANIFEST.format(uid=uid, name=name, entry=entry)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("MANIFEST/manifest.xml", manifest)
        z.writestr(entry, cot_xml)
    return buf.getvalue()
