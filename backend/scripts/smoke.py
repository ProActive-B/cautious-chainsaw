"""Manual smoke test: exercises the API functions and prints a sample report."""

from app.main import assess, health, layers, meta
from app.models import AssessRequest
from app.taxonomy import Profile


def main() -> None:
    print("HEALTH:", health())
    m = meta()
    print("PROFILES:", len(m["profiles"]), "CMs:", len(m["countermeasures"]), "view:", m["default_view"])
    lyr = layers()
    print("LAYERS:", {k: len(v["features"]) for k, v in lyr.items()})

    for profile in (Profile.CI_OWNER, Profile.FEDERAL_124N, Profile.STATE_LOCAL_LE_CERTIFIED):
        rep = assess(AssessRequest(profile=profile, lat=32.95, lon=-96.65, credible_threat=True))
        print(f"\n=== {profile.value} @ pilot site ===")
        print("Location:", rep.location.place_label, "| airspace", rep.location.airspace_class,
              "| nearest", rep.location.nearest_airport, rep.location.nearest_airport_distance_nm, "nm",
              "| flags", rep.location.location_flags)
        print("PERMITTED:", [(a.label, a.risk.band) for a in rep.permitted])
        print("CONDITIONAL:", [(a.label, a.risk.band if a.risk else None) for a in rep.conditional])
        print("PROHIBITED:", [a.label for a in rep.prohibited])
        print("DOC PATHWAYS:", [d.title for d in rep.documentation])


if __name__ == "__main__":
    main()
